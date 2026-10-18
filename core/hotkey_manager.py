import keyboard
from PySide6.QtCore import QObject, Signal
from core.config import config

class HotkeyManager(QObject):
    sig_record_toggle = Signal()
    sig_record_pause = Signal()
    sig_screenshot_full = Signal()
    sig_screenshot_snip = Signal()

    def __init__(self):
        super().__init__()
        self._registered_handlers = []
        self.is_active = False

    def register_all(self):
        """Register global hotkeys defined in config."""
        self.unregister_all()

        if not config.get("hotkeys_enabled", True):
            self.is_active = False
            return True

        success = True
        # 1. Record toggle (Start / Stop)
        key_toggle = config.get("hotkey_record_toggle", "F9").strip().lower()
        if key_toggle:
            try:
                h = keyboard.add_hotkey(key_toggle, self._on_record_toggle)
                self._registered_handlers.append(h)
            except Exception as e:
                print(f"[HotkeyManager] Error registering {key_toggle}: {e}")
                success = False

        # 2. Record pause / resume
        key_pause = config.get("hotkey_record_pause", "F10").strip().lower()
        if key_pause:
            try:
                h = keyboard.add_hotkey(key_pause, self._on_record_pause)
                self._registered_handlers.append(h)
            except Exception as e:
                print(f"[HotkeyManager] Error registering {key_pause}: {e}")
                success = False

        # 3. Screenshot full
        key_snap_full = config.get("hotkey_screenshot_full", "F11").strip().lower()
        if key_snap_full:
            try:
                h = keyboard.add_hotkey(key_snap_full, self._on_screenshot_full)
                self._registered_handlers.append(h)
            except Exception as e:
                print(f"[HotkeyManager] Error registering {key_snap_full}: {e}")
                success = False

        # 4. Screenshot snip
        key_snap_snip = config.get("hotkey_screenshot_snip", "F12").strip().lower()
        if key_snap_snip:
            try:
                h = keyboard.add_hotkey(key_snap_snip, self._on_screenshot_snip)
                self._registered_handlers.append(h)
            except Exception as e:
                print(f"[HotkeyManager] Error registering {key_snap_snip}: {e}")
                success = False

        self.is_active = len(self._registered_handlers) > 0
        return success

    def unregister_all(self):
        """Safely remove all registered global hotkeys."""
        for h in self._registered_handlers:
            try:
                keyboard.remove_hotkey(h)
            except Exception:
                pass
        self._registered_handlers.clear()
        self.is_active = False

    def reload(self):
        return self.register_all()

    def _on_record_toggle(self):
        self.sig_record_toggle.emit()

    def _on_record_pause(self):
        self.sig_record_pause.emit()

    def _on_screenshot_full(self):
        self.sig_screenshot_full.emit()

    def _on_screenshot_snip(self):
        self.sig_screenshot_snip.emit()

# Global singleton
hotkey_manager = HotkeyManager()
