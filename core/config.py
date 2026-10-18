import os
import json
from pathlib import Path

DEFAULT_CONFIG = {
    "save_dir_video": str(Path.home() / "Videos" / "ScreenRecords"),
    "save_dir_screenshot": str(Path.home() / "Pictures" / "Screenshots"),
    "fps": 60,
    "quality": "medium",  # "high", "medium", "low"
    "encoder": "auto",  # "auto", "h264_amf", "h264_mf", "h264_nvenc", "libx264"
    "record_cursor": True,
    "record_audio": False,
    "audio_device": "Default",
    "auto_copy_clipboard": True,
    "monitor_index": 0,
    "capture_region": None,  # None for full screen or [left, top, right, bottom]
    "hotkeys_enabled": True,
    "hotkey_record_toggle": "F9",
    "hotkey_record_pause": "F10",
    "hotkey_screenshot_full": "F11",
    "hotkey_screenshot_snip": "F12"
}

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"

class ConfigManager:
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config.update(data)
            except Exception as e:
                print(f"[Config] Failed to load config: {e}")
        # Ensure output directories exist
        os.makedirs(self.config["save_dir_video"], exist_ok=True)
        os.makedirs(self.config["save_dir_screenshot"], exist_ok=True)

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Failed to save config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

# Global singleton
config = ConfigManager()
