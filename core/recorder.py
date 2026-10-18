import os
import sys
import time
import datetime
import subprocess
import threading
from pathlib import Path
from typing import Tuple, List, Dict
import numpy as np
from PySide6.QtCore import QObject, Signal

import imageio_ffmpeg
from core.desktop_utils import ensure_default_desktop, get_cursor_info, draw_cursor_on_frame
from core.audio_recorder import AudioRecorder
from core.config import config
import bettercam

AVAILABLE_ENCODERS = {
    "auto": "Tự động (GPU Tăng tốc phần cứng - Khuyên dùng)",
    "h264_amf": "AMD AMF (Card AMD Radeon)",
    "h264_mf": "Windows MediaFoundation (GPU chuẩn Windows)",
    "h264_nvenc": "NVIDIA NVENC (Card đồ họa NVIDIA)",
    "h264_qsv": "Intel Quick Sync (Card đồ họa Intel)",
    "libx264": "CPU Phần mềm (libx264 - Tốn CPU)"
}

_cached_supported_encoders: Dict[str, bool] = {}
_cached_best_encoder: str = ""

def test_encoder(encoder_name: str) -> bool:
    """Kiểm tra xem encoder FFmpeg có hoạt động trên máy không."""
    if encoder_name in _cached_supported_encoders:
        return _cached_supported_encoders[encoder_name]

    if encoder_name == "libx264":
        _cached_supported_encoders["libx264"] = True
        return True

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        cmd = [
            ffmpeg_exe, "-y",
            "-f", "lavfi", "-i", "nullsrc=s=256x256:d=0.05:r=30",
            "-c:v", encoder_name,
            "-f", "null", "-"
        ]
        res = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
            timeout=3
        )
        supported = (res.returncode == 0)
    except Exception as e:
        print(f"[Recorder] Encoder {encoder_name} test failed: {e}")
        supported = False

    _cached_supported_encoders[encoder_name] = supported
    return supported

def detect_best_hardware_encoder() -> str:
    """Tự động tìm kiếm GPU Hardware Encoder tối ưu nhất trên máy."""
    global _cached_best_encoder
    if _cached_best_encoder:
        return _cached_best_encoder

    # Thứ tự ưu tiên: NVENC -> AMF -> QSV -> MF -> libx264
    candidates = ["h264_nvenc", "h264_amf", "h264_qsv", "h264_mf"]
    for enc in candidates:
        if test_encoder(enc):
            _cached_best_encoder = enc
            print(f"[Recorder] Detected optimal GPU hardware encoder: {enc}")
            return enc

    print("[Recorder] No GPU hardware encoder available, falling back to libx264 (CPU)")
    _cached_best_encoder = "libx264"
    return "libx264"

def get_encoder_args(encoder_choice: str, quality: str) -> Tuple[str, List[str]]:
    """Xác định encoder và bộ tham số FFmpeg tối ưu."""
    if encoder_choice == "auto" or not encoder_choice:
        chosen_enc = detect_best_hardware_encoder()
    else:
        if test_encoder(encoder_choice):
            chosen_enc = encoder_choice
        else:
            print(f"[Recorder] Encoder '{encoder_choice}' not available, falling back to auto-detect.")
            chosen_enc = detect_best_hardware_encoder()

    args: List[str] = []

    if chosen_enc == "h264_nvenc":
        cq_map = {"high": "19", "medium": "23", "low": "28"}
        cq = cq_map.get(quality, "23")
        args = [
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-tune", "ll",
            "-rc", "vbr",
            "-cq", cq,
            "-b:v", "0"
        ]
    elif chosen_enc == "h264_amf":
        bitrate_map = {"high": "8M", "medium": "4.5M", "low": "2.5M"}
        usage_map = {"high": "lowlatency_high_quality", "medium": "lowlatency", "low": "lowlatency"}
        args = [
            "-c:v", "h264_amf",
            "-usage", usage_map.get(quality, "lowlatency"),
            "-rc", "cbr",
            "-b:v", bitrate_map.get(quality, "4.5M")
        ]
    elif chosen_enc == "h264_mf":
        quality_map = {"high": "80", "medium": "70", "low": "55"}
        q_val = quality_map.get(quality, "70")
        args = [
            "-c:v", "h264_mf",
            "-scenario", "camera_record",
            "-rate_control", "quality",
            "-quality", q_val
        ]
    elif chosen_enc == "h264_qsv":
        gq_map = {"high": "20", "medium": "24", "low": "28"}
        args = [
            "-c:v", "h264_qsv",
            "-preset", "veryfast",
            "-global_quality", gq_map.get(quality, "24")
        ]
    else:
        crf_map = {"high": "18", "medium": "22", "low": "26"}
        args = [
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-crf", crf_map.get(quality, "22")
        ]

    return chosen_enc, args

class ScreenRecorder(QObject):
    # Signals for UI
    sig_started = Signal(str)  # output_path
    sig_tick = Signal(float, float, int)  # duration_sec, current_fps, frame_count
    sig_paused = Signal()
    sig_resumed = Signal()
    sig_stopped = Signal(str, float, int, int)  # output_path, duration_sec, frame_count, file_size_bytes
    sig_error = Signal(str)

    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.is_paused = False
        self._stop_requested = False
        self.thread = None
        self.audio_recorder = AudioRecorder()
        self.active_encoder = ""

    def start_recording(
        self,
        monitor_idx=0,
        region=None,
        fps=60,
        quality="medium",
        encoder="auto",
        record_cursor=True,
        record_audio=False,
        audio_device_idx=None
    ):
        if self.is_recording:
            return False

        self.monitor_idx = monitor_idx
        self.region = region
        self.target_fps = int(fps)
        self.quality = quality
        self.encoder_setting = encoder
        self.record_cursor = record_cursor
        self.record_audio = record_audio
        self.audio_device_idx = audio_device_idx

        self.is_recording = True
        self.is_paused = False
        self._stop_requested = False

        self.thread = threading.Thread(target=self._record_worker, daemon=True)
        self.thread.start()
        return True

    def pause_recording(self):
        if self.is_recording and not self.is_paused:
            self.is_paused = True
            if self.record_audio:
                self.audio_recorder.pause()
            self.sig_paused.emit()

    def resume_recording(self):
        if self.is_recording and self.is_paused:
            self.is_paused = False
            if self.record_audio:
                self.audio_recorder.resume()
            self.sig_resumed.emit()

    def stop_recording(self):
        if not self.is_recording:
            return
        self._stop_requested = True

    def _record_worker(self):
        ensure_default_desktop()
        save_dir = config.get("save_dir_video")
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        final_video_path = os.path.join(save_dir, f"Record_{timestamp}.mp4")
        temp_video_path = os.path.join(save_dir, f"temp_rec_{timestamp}.mp4") if self.record_audio else final_video_path

        # Resolve encoder configuration
        actual_encoder, encoder_args = get_encoder_args(self.encoder_setting, self.quality)
        self.active_encoder = actual_encoder
        print(f"[Recorder] Active encoder for this session: {actual_encoder}")

        # Initialize BetterCam
        cam = None
        proc = None
        try:
            cam = bettercam.create(output_idx=self.monitor_idx, output_color="BGR")
            if cam is None:
                raise RuntimeError("Không thể tạo đối tượng BetterCam cho màn hình đã chọn.")

            # Grab test frame to get resolution
            test_frame = None
            for _ in range(5):
                test_frame = cam.grab(region=self.region)
                if test_frame is not None:
                    break
                time.sleep(0.02)

            if test_frame is None:
                # Try full screen
                full = cam.grab()
                if full is not None and self.region is not None:
                    l, t, r, b = self.region
                    test_frame = full[t:b, l:r]
                elif full is not None:
                    test_frame = full

            if test_frame is None:
                raise RuntimeError("Không thể đọc khung hình từ card đồ họa qua DXGI.")

            h, w = test_frame.shape[:2]
            # FFmpeg requires dimensions divisible by 2 for yuv420p
            if w % 2 != 0 or h % 2 != 0:
                w = w - (w % 2)
                h = h - (h % 2)

            # Start audio recording if requested
            if self.record_audio:
                self.audio_recorder.start(device_idx=self.audio_device_idx)

            # Setup FFmpeg process with GPU hardware acceleration
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_exe,
                "-y",
                "-f", "rawvideo",
                "-vcodec", "rawvideo",
                "-s", f"{w}x{h}",
                "-pix_fmt", "bgr24",
                "-r", str(self.target_fps),
                "-i", "-"
            ] + encoder_args + [
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                temp_video_path
            ]

            # Prevent CMD console window from popping up on Windows
            creation_flags = 0
            startupinfo = None
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                bufsize=10**7,
                creationflags=creation_flags,
                startupinfo=startupinfo
            )

            # Pre-allocate contiguous crop buffer if region recording
            crop_buffer = np.empty((h, w, 3), dtype=np.uint8) if self.region is not None else None

            # Start BetterCam continuous video mode
            cam.start(target_fps=self.target_fps, video_mode=True)
            self.sig_started.emit(final_video_path)

            frame_interval = 1.0 / self.target_fps
            start_perf = time.perf_counter()
            frame_count = 0
            last_valid_frame = test_frame[:h, :w]
            if not last_valid_frame.flags['C_CONTIGUOUS']:
                last_valid_frame = np.ascontiguousarray(last_valid_frame)

            fps_calc_time = start_perf
            fps_calc_frames = 0
            current_fps = float(self.target_fps)
            paused_accumulated_time = 0.0

            off_x = self.region[0] if self.region else 0
            off_y = self.region[1] if self.region else 0

            # High performance zero-copy recording loop
            while not self._stop_requested:
                if self.is_paused:
                    pause_tick = time.perf_counter()
                    time.sleep(0.05)
                    paused_accumulated_time += (time.perf_counter() - pause_tick)
                    continue

                # Get latest frame from BetterCam
                frame = cam.get_latest_frame()
                if frame is not None:
                    if self.region is not None and crop_buffer is not None:
                        l, t, r, b = self.region
                        np.copyto(crop_buffer, frame[t:b, l:r])
                        frame = crop_buffer
                    elif frame.shape[0] != h or frame.shape[1] != w:
                        frame = frame[:h, :w]
                    last_valid_frame = frame
                else:
                    frame = last_valid_frame

                # Overlay cursor using lightweight 32x32 ROI backup (avoids full-frame 6MB copies)
                cursor_drawn = False
                roi_backup = None
                x1 = y1 = x2 = y2 = 0

                if self.record_cursor:
                    cur_vis, cx, cy = get_cursor_info()
                    if cur_vis:
                        cx_local = cx - off_x
                        cy_local = cy - off_y
                        if 0 <= cx_local < w and 0 <= cy_local < h:
                            x1, y1 = max(0, cx_local), max(0, cy_local)
                            x2, y2 = min(w, cx_local + 32), min(h, cy_local + 32)
                            roi_backup = frame[y1:y2, x1:x2].copy()
                            draw_cursor_on_frame(frame, cx, cy, off_x, off_y)
                            cursor_drawn = True

                # Zero-copy memoryview pipe write
                try:
                    if frame.flags['C_CONTIGUOUS']:
                        proc.stdin.write(memoryview(frame))
                    else:
                        proc.stdin.write(frame.tobytes())
                except (BrokenPipeError, OSError):
                    break
                finally:
                    # Restore ROI to keep BetterCam frame pristine
                    if cursor_drawn and roi_backup is not None:
                        frame[y1:y2, x1:x2] = roi_backup

                frame_count += 1
                fps_calc_frames += 1

                # Calculate live FPS & duration
                now = time.perf_counter()
                if now - fps_calc_time >= 0.5:
                    current_fps = fps_calc_frames / (now - fps_calc_time)
                    fps_calc_time = now
                    fps_calc_frames = 0
                    elapsed_duration = (now - start_perf) - paused_accumulated_time
                    self.sig_tick.emit(elapsed_duration, current_fps, frame_count)

            # Loop finished, finalize video
            cam.stop()
            cam.release()
            cam = None

            if proc and proc.stdin:
                proc.stdin.close()
                proc.wait()
                proc = None

            # Stop audio and mux if needed
            audio_path = None
            if self.record_audio:
                audio_path = self.audio_recorder.stop()

            # If audio was recorded, mux audio with video
            if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 100:
                mux_cmd = [
                    ffmpeg_exe,
                    "-y",
                    "-i", temp_video_path,
                    "-i", audio_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    final_video_path
                ]
                try:
                    subprocess.run(
                        mux_cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=creation_flags,
                        startupinfo=startupinfo,
                        check=True
                    )
                    if temp_video_path != final_video_path and os.path.exists(temp_video_path):
                        os.remove(temp_video_path)
                except Exception as e:
                    print(f"[Recorder] Mux audio error: {e}, keeping video only.")
                    if temp_video_path != final_video_path and os.path.exists(temp_video_path):
                        os.rename(temp_video_path, final_video_path)
            elif temp_video_path != final_video_path and os.path.exists(temp_video_path):
                os.rename(temp_video_path, final_video_path)

            self.audio_recorder.cleanup()

            total_duration = frame_count / self.target_fps if self.target_fps > 0 else 0
            file_size = os.path.getsize(final_video_path) if os.path.exists(final_video_path) else 0

            self.sig_stopped.emit(final_video_path, total_duration, frame_count, file_size)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.sig_error.emit(str(e))
        finally:
            if cam is not None:
                try:
                    cam.stop()
                    cam.release()
                except Exception:
                    pass
            if proc is not None and proc.stdin:
                try:
                    proc.stdin.close()
                    proc.wait()
                except Exception:
                    pass
            self.is_recording = False
            self.is_paused = False
            self._stop_requested = False

# Global instance
recorder = ScreenRecorder()
