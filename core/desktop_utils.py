import ctypes
from ctypes import wintypes
import numpy as np
import cv2

# Windows structures for cursor
class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HANDLE),
        ("ptScreenPos", POINT)
    ]

CURSOR_SHOWING = 0x00000001

def ensure_default_desktop():
    """Ensure the calling thread is connected to Windows interactive Default desktop."""
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
            return True
    except Exception as e:
        print(f"[DesktopUtils] Failed to set Default desktop: {e}")
    return False

def enable_dpi_awareness():
    """Set high-DPI awareness on Windows so coordinate space matches real pixels."""
    try:
        # Per-monitor DPI aware v2
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            # Fallback to per-monitor DPI aware
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

def get_cursor_info():
    """Return (visible, x, y)."""
    try:
        user32 = ctypes.windll.user32
        ci = CURSORINFO()
        ci.cbSize = ctypes.sizeof(CURSORINFO)
        if user32.GetCursorInfo(ctypes.byref(ci)):
            visible = bool(ci.flags & CURSOR_SHOWING)
            return visible, int(ci.ptScreenPos.x), int(ci.ptScreenPos.y)
    except Exception:
        pass
    return False, 0, 0

# Pre-defined cursor arrow polygon vertices (scaled 1x and 1.5x)
CURSOR_POLY = np.array([
    [0, 0],
    [0, 19],
    [5, 15],
    [9, 23],
    [12, 21],
    [8, 14],
    [14, 14]
], dtype=np.int32)

def draw_cursor_on_frame(frame: np.ndarray, x: int, y: int, offset_x: int = 0, offset_y: int = 0):
    """
    Draw a crisp Windows-style mouse cursor onto the numpy frame.
    frame: (H, W, 3) BGR or RGB image
    x, y: Global screen coordinates
    offset_x, offset_y: Top-left of capture region
    """
    cx = x - offset_x
    cy = y - offset_y
    h, w = frame.shape[:2]

    # Check bounds
    if not (0 <= cx < w and 0 <= cy < h):
        return frame

    # Shift cursor polygon to (cx, cy)
    pts = CURSOR_POLY + [cx, cy]
    
    # Clip points within frame bounds
    # Draw dark shadow / border
    cv2.polylines(frame, [pts], isClosed=True, color=(15, 15, 15), thickness=3, lineType=cv2.LINE_AA)
    # Fill cursor with clean bright white
    cv2.fillPoly(frame, [pts], color=(250, 250, 250), lineType=cv2.LINE_AA)

    return frame
