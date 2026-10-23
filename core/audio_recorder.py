import os
import time
import tempfile
import threading
import wave
from typing import List, Dict, Optional, Tuple
import pyaudiowpatch as pyaudio

class AudioRecorder:
    def __init__(self):
        self.is_recording = False
        self.is_paused = False
        self._running = False
        self._threads: List[threading.Thread] = []
        self._streams = []
        self._pa: Optional[pyaudio.PyAudio] = None
        self.temp_files: List[str] = []
        self._lock = threading.Lock()
        self._recorded_data: Dict[str, List[bytes]] = {}
        self._stream_specs: Dict[str, dict] = {}

    def get_system_devices(self) -> List[Dict]:
        """Return available WASAPI loopback output devices (Speakers/Headphones)."""
        devices = []
        pa = None
        try:
            pa = pyaudio.PyAudio()
            wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_out_idx = wasapi_info.get('defaultOutputDevice', -1)
            default_out_name = ""
            if default_out_idx >= 0:
                try:
                    default_out_name = pa.get_device_info_by_index(default_out_idx).get('name', '')
                except Exception:
                    pass

            for d in pa.get_loopback_device_info_generator():
                raw_name = d.get('name', '')
                clean_name = raw_name.replace(" [Loopback]", "").strip()
                is_def = bool(default_out_name and default_out_name in raw_name)
                devices.append({
                    "index": d['index'],
                    "name": clean_name,
                    "is_default": is_def,
                    "raw_name": raw_name,
                    "channels": d.get('maxInputChannels', 2),
                    "samplerate": int(d.get('defaultSampleRate', 48000))
                })
        except Exception as e:
            print(f"[Audio] Error getting system loopback devices: {e}")
        finally:
            if pa is not None:
                try:
                    pa.terminate()
                except Exception:
                    pass
        return devices

    def get_mic_devices(self) -> List[Dict]:
        """Return available microphone input devices."""
        devices = []
        pa = None
        try:
            pa = pyaudio.PyAudio()
            wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            def_in_idx = wasapi_info.get('defaultInputDevice', -1)

            for i in range(pa.get_device_count()):
                d = pa.get_device_info_by_index(i)
                # Must have input channels and NOT be a loopback device
                if d.get('maxInputChannels', 0) > 0 and not d.get('isLoopbackDevice', False):
                    # Filter for WASAPI devices for optimal compatibility
                    host_api = pa.get_host_api_info_by_index(d.get('hostApi', 0))
                    if 'WASAPI' in host_api.get('name', ''):
                        devices.append({
                            "index": d['index'],
                            "name": d.get('name', ''),
                            "is_default": (i == def_in_idx),
                            "channels": min(2, d.get('maxInputChannels', 1)),
                            "samplerate": int(d.get('defaultSampleRate', 48000))
                        })
            # Fallback if no WASAPI mic found
            if not devices:
                for i in range(pa.get_device_count()):
                    d = pa.get_device_info_by_index(i)
                    if d.get('maxInputChannels', 0) > 0 and not d.get('isLoopbackDevice', False):
                        devices.append({
                            "index": d['index'],
                            "name": d.get('name', ''),
                            "is_default": (i == pa.get_default_input_device_info().get('index', -1)),
                            "channels": min(2, d.get('maxInputChannels', 1)),
                            "samplerate": int(d.get('defaultSampleRate', 48000))
                        })
        except Exception as e:
            print(f"[Audio] Error getting mic devices: {e}")
        finally:
            if pa is not None:
                try:
                    pa.terminate()
                except Exception:
                    pass
        return devices

    def get_audio_devices(self) -> List[Tuple[int, str]]:
        """Legacy helper for backward compatibility."""
        mics = self.get_mic_devices()
        return [(m['index'], m['name']) for m in mics]

    def _resolve_devices(self, source: str, sys_idx: Optional[int], mic_idx: Optional[int]):
        """Find the exact PyAudio device info dicts for system and/or mic."""
        sys_dev = None
        mic_dev = None

        if source in ("system", "both"):
            loopbacks = list(self._pa.get_loopback_device_info_generator())
            if sys_idx is not None:
                for d in loopbacks:
                    if d['index'] == sys_idx:
                        sys_dev = d
                        break
            if sys_dev is None and loopbacks:
                # Find default speaker's loopback
                try:
                    wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
                    def_out = self._pa.get_device_info_by_index(wasapi_info['defaultOutputDevice'])
                    for lb in loopbacks:
                        if def_out['name'] in lb['name']:
                            sys_dev = lb
                            break
                except Exception:
                    pass
                if sys_dev is None:
                    sys_dev = loopbacks[0]

        if source in ("mic", "both"):
            if mic_idx is not None:
                try:
                    d = self._pa.get_device_info_by_index(mic_idx)
                    if d.get('maxInputChannels', 0) > 0:
                        mic_dev = d
                except Exception:
                    pass
            if mic_dev is None:
                try:
                    wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
                    def_in_idx = wasapi_info.get('defaultInputDevice', -1)
                    if def_in_idx >= 0:
                        mic_dev = self._pa.get_device_info_by_index(def_in_idx)
                except Exception:
                    pass
                if mic_dev is None:
                    try:
                        mic_dev = self._pa.get_default_input_device_info()
                    except Exception:
                        pass

        return sys_dev, mic_dev

    def start(self, source: str = "system", system_device_idx: Optional[int] = None, mic_device_idx: Optional[int] = None) -> bool:
        """
        Start recording audio.
        source: 'system' (computer audio), 'mic' (microphone), or 'both' (mixed)
        """
        self.stop()

        self._pa = pyaudio.PyAudio()
        sys_dev, mic_dev = self._resolve_devices(source, system_device_idx, mic_device_idx)

        self._recorded_data = {}
        self._stream_specs = {}
        self._streams = []
        self._threads = []
        self.temp_files = []

        chunk_size = 1024

        # 1. Open System Loopback stream if requested
        if source in ("system", "both") and sys_dev is not None:
            try:
                channels = sys_dev.get('maxInputChannels', 2)
                rate = int(sys_dev.get('defaultSampleRate', 48000))
                stream_sys = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=rate,
                    frames_per_buffer=chunk_size,
                    input=True,
                    input_device_index=sys_dev['index']
                )
                self._streams.append(stream_sys)
                self._recorded_data['system'] = []
                self._stream_specs['system'] = {
                    "channels": channels,
                    "rate": rate,
                    "sampwidth": self._pa.get_sample_size(pyaudio.paInt16)
                }
                print(f"[Audio] Started SYSTEM loopback capture: {sys_dev['name']} ({rate}Hz, {channels}ch)")
            except Exception as e:
                print(f"[Audio] Failed to open system loopback stream: {e}")

        # 2. Open Mic stream if requested
        if source in ("mic", "both") and mic_dev is not None:
            try:
                channels = min(2, mic_dev.get('maxInputChannels', 1))
                rate = int(mic_dev.get('defaultSampleRate', 48000))
                stream_mic = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=rate,
                    frames_per_buffer=chunk_size,
                    input=True,
                    input_device_index=mic_dev['index']
                )
                self._streams.append(stream_mic)
                self._recorded_data['mic'] = []
                self._stream_specs['mic'] = {
                    "channels": channels,
                    "rate": rate,
                    "sampwidth": self._pa.get_sample_size(pyaudio.paInt16)
                }
                print(f"[Audio] Started MIC capture: {mic_dev['name']} ({rate}Hz, {channels}ch)")
            except Exception as e:
                print(f"[Audio] Failed to open microphone stream: {e}")

        if not self._streams:
            print("[Audio] No audio streams could be opened!")
            if self._pa is not None:
                self._pa.terminate()
                self._pa = None
            return False

        self._running = True
        self.is_recording = True
        self.is_paused = False

        # Launch worker thread for each active stream
        stream_keys = list(self._recorded_data.keys())
        for idx, key in enumerate(stream_keys):
            st = self._streams[idx]
            t = threading.Thread(target=self._worker, args=(key, st, chunk_size), daemon=True)
            self._threads.append(t)
            t.start()

        return True

    def _worker(self, key: str, stream, chunk_size: int):
        while self._running:
            try:
                data = stream.read(chunk_size, exception_on_overflow=False)
                if not self.is_paused:
                    with self._lock:
                        self._recorded_data[key].append(data)
            except Exception as e:
                if self._running:
                    print(f"[Audio] Read error on {key} stream: {e}")
                break

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self) -> Dict[str, str]:
        """
        Stop recording and save WAV files.
        Returns dict of filepaths: e.g. {'system': '...', 'mic': '...'}
        """
        if not self.is_recording and not self._running:
            return {}

        self._running = False
        self.is_recording = False
        self.is_paused = False

        # Wait for threads to complete reading
        for t in self._threads:
            t.join(timeout=1.0)
        self._threads = []

        # Stop and close streams
        for st in self._streams:
            try:
                st.stop_stream()
                st.close()
            except Exception:
                pass
        self._streams = []

        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None

        output_files: Dict[str, str] = {}
        temp_dir = tempfile.gettempdir()
        timestamp = int(time.time() * 1000)

        with self._lock:
            for key, frames in self._recorded_data.items():
                if not frames or key not in self._stream_specs:
                    continue
                spec = self._stream_specs[key]
                file_path = os.path.join(temp_dir, f"audio_{key}_{timestamp}.wav")
                try:
                    wf = wave.open(file_path, 'wb')
                    wf.setnchannels(spec['channels'])
                    wf.setsampwidth(spec['sampwidth'])
                    wf.setframerate(spec['rate'])
                    wf.writeframes(b''.join(frames))
                    wf.close()
                    output_files[key] = file_path
                    self.temp_files.append(file_path)
                    duration_s = (len(frames) * 1024) / spec['rate']
                    print(f"[Audio] Saved {key} audio ({duration_s:.1f}s) to: {file_path}")
                except Exception as e:
                    print(f"[Audio] Error writing {key} WAV: {e}")

            self._recorded_data = {}

        return output_files

    def cleanup(self):
        """Delete temporary audio files."""
        for f in self.temp_files:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        self.temp_files = []
