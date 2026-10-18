import threading
import tempfile
import os
import numpy as np
import sounddevice as sd
import soundfile as sf

class AudioRecorder:
    def __init__(self):
        self.is_recording = False
        self.is_paused = False
        self.frames = []
        self.stream = None
        self.samplerate = 48000
        self.channels = 2
        self.temp_file = None
        self._lock = threading.Lock()

    def get_audio_devices(self):
        """Return list of input audio devices."""
        devices = []
        try:
            devs = sd.query_devices()
            for idx, d in enumerate(devs):
                if d.get('max_input_channels', 0) > 0:
                    devices.append((idx, d['name']))
        except Exception as e:
            print(f"[Audio] Error querying devices: {e}")
        return devices

    def start(self, device_idx=None):
        """Start audio recording thread."""
        self.frames = []
        self.is_recording = True
        self.is_paused = False
        
        # Create temp file for audio
        temp_dir = tempfile.gettempdir()
        self.temp_file = os.path.join(temp_dir, f"audio_rec_{os.getpid()}_{id(self)}.wav")

        def audio_callback(indata, frame_count, time_info, status):
            if self.is_recording and not self.is_paused:
                with self._lock:
                    self.frames.append(indata.copy())

        try:
            # Query device info for channels and sample rate
            if device_idx is not None:
                dev_info = sd.query_devices(device_idx, 'input')
                self.channels = min(2, dev_info.get('max_input_channels', 2))
                self.samplerate = int(dev_info.get('default_samplerate', 48000))

            self.stream = sd.InputStream(
                device=device_idx,
                channels=self.channels,
                samplerate=self.samplerate,
                dtype='float32',
                callback=audio_callback
            )
            self.stream.start()
            print(f"[Audio] Recording started on device {device_idx} at {self.samplerate}Hz {self.channels}ch")
            return True
        except Exception as e:
            print(f"[Audio] Failed to start stream: {e}")
            self.is_recording = False
            self.temp_file = None
            return False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        """Stop audio stream and write to temp WAV file. Returns path to WAV file or None."""
        if not self.is_recording:
            return None

        self.is_recording = False
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
        except Exception as e:
            print(f"[Audio] Error closing stream: {e}")

        with self._lock:
            if not self.frames or self.temp_file is None:
                return None
            data = np.concatenate(self.frames, axis=0)

        try:
            sf.write(self.temp_file, data, self.samplerate)
            print(f"[Audio] Saved {len(data) / self.samplerate:.2f}s audio to {self.temp_file}")
            return self.temp_file
        except Exception as e:
            print(f"[Audio] Failed to save WAV file: {e}")
            return None

    def cleanup(self):
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except Exception:
                pass
            self.temp_file = None
