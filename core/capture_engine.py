import os
import time
import datetime
from pathlib import Path
import numpy as np
from PIL import Image
from PySide6.QtGui import QImage, QClipboard, QGuiApplication
import bettercam

from core.desktop_utils import ensure_default_desktop, get_cursor_info, draw_cursor_on_frame
from core.config import config

class CaptureEngine:
    def __init__(self):
        self.camera = None
        self.current_monitor_idx = None
        self.current_color = "BGR"

    def get_monitors(self):
        """List available monitors."""
        ensure_default_desktop()
        monitors = []
        try:
            # bettercam has bettercam.output_info()
            # or enumerate via outputs
            # Let's parse device_info and output_info
            import comtypes
            info_str = bettercam.output_info()
            # Also can check bettercam.__factory
            # E.g., 'Outputs: Device[0] Output[0]: Res:(2560, 1440) Rot:0 Primary:True'
            lines = [line.strip() for line in info_str.strip().split('\n') if 'Output' in line]
            for idx, line in enumerate(lines):
                monitors.append({
                    "index": idx,
                    "name": f"Monitor {idx + 1}",
                    "details": line
                })
        except Exception as e:
            print(f"[CaptureEngine] Error getting monitors: {e}")
            monitors.append({"index": 0, "name": "Monitor 1 (Mặc định)", "details": "Primary Monitor"})
        return monitors if monitors else [{"index": 0, "name": "Monitor 1 (Mặc định)", "details": "Primary Monitor"}]

    def get_camera(self, monitor_idx=0, output_color="BGR"):
        """Get or initialize BetterCam instance."""
        ensure_default_desktop()
        if self.camera is not None and self.current_monitor_idx == monitor_idx and self.current_color == output_color:
            return self.camera

        self.release()
        try:
            self.camera = bettercam.create(
                output_idx=monitor_idx,
                output_color=output_color
            )
            self.current_monitor_idx = monitor_idx
            self.current_color = output_color
            print(f"[CaptureEngine] Initialized BetterCam for monitor {monitor_idx}")
            return self.camera
        except Exception as e:
            print(f"[CaptureEngine] Failed to create BetterCam: {e}")
            return None

    def release(self):
        if self.camera is not None:
            try:
                if getattr(self.camera, 'is_capturing', False):
                    self.camera.stop()
                self.camera.release()
            except Exception as e:
                print(f"[CaptureEngine] Release exception: {e}")
            finally:
                self.camera = None
                self.current_monitor_idx = None

    def capture_screenshot(self, monitor_idx=0, region=None, include_cursor=False, copy_to_clipboard=True):
        """
        Capture an instant high-resolution screenshot.
        region: tuple (left, top, right, bottom) or None for full screen
        Returns dict with filepath, dimensions, size, and QImage.
        """
        ensure_default_desktop()
        cam = self.get_camera(monitor_idx=monitor_idx, output_color="BGR")
        if cam is None:
            raise RuntimeError("Không thể khởi tạo BetterCam để chụp màn hình!")

        frame = None
        # Try grab with a few retries if desktop buffer is updating
        for _ in range(5):
            frame = cam.grab(region=region)
            if frame is not None:
                break
            time.sleep(0.01)

        if frame is None:
            # Fallback grab without region and crop if needed
            full_frame = cam.grab()
            if full_frame is not None and region is not None:
                l, t, r, b = region
                frame = full_frame[t:b, l:r]
            elif full_frame is not None:
                frame = full_frame

        if frame is None:
            raise RuntimeError("Không thể lấy dữ liệu khung hình từ màn hình!")

        # Make copy so we can modify
        frame = frame.copy()

        # Overlay cursor if requested
        if include_cursor:
            cur_vis, cur_x, cur_y = get_cursor_info()
            if cur_vis:
                off_x = region[0] if region else 0
                off_y = region[1] if region else 0
                draw_cursor_on_frame(frame, cur_x, cur_y, off_x, off_y)

        # Convert BGR to RGB for saving and display
        h, w, c = frame.shape
        rgb_frame = np.ascontiguousarray(frame[:, :, ::-1])

        # Generate filename and save to configured folder
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = config.get("save_dir_screenshot")
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, f"Screenshot_{timestamp}.png")

        # Save with PIL
        pil_img = Image.fromarray(rgb_frame)
        pil_img.save(file_path, "PNG", optimize=True)
        file_size = os.path.getsize(file_path)

        # Convert to QImage
        bytes_per_line = 3 * w
        qimage = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()

        # Copy to Windows clipboard
        if copy_to_clipboard:
            clipboard = QGuiApplication.clipboard()
            if clipboard is not None:
                clipboard.setImage(qimage, QClipboard.Mode.Clipboard)

        return {
            "path": file_path,
            "filename": os.path.basename(file_path),
            "width": w,
            "height": h,
            "size_bytes": file_size,
            "qimage": qimage,
            "timestamp": timestamp
        }

# Global instance
capture_engine = CaptureEngine()
