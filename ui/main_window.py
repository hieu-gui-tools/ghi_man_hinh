import os
import sys
import subprocess
import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QCheckBox, QTabWidget,
    QFileDialog, QMessageBox, QListWidget, QListWidgetItem,
    QFrame, QScrollArea, QSplitter, QLineEdit, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import Qt, QTimer, Slot, QUrl
from PySide6.QtGui import QIcon, QPixmap, QDesktopServices, QGuiApplication, QClipboard, QCloseEvent, QAction

from core.config import config
from core.capture_engine import capture_engine
from core.recorder import recorder
from core.audio_recorder import AudioRecorder
from core.hotkey_manager import hotkey_manager
from ui.widgets import PulsingDot, StatCard
from ui.snip_overlay import SnipOverlay

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ScreenRecorder Pro - BetterCam DXGI")
        self.resize(880, 690)
        self.setMinimumSize(800, 600)

        # Set App Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.custom_region = None
        self.audio_recorder_helper = AudioRecorder()
        self.snip_overlay = SnipOverlay()
        self.snip_overlay.region_selected.connect(self.on_region_selected)
        self.snip_overlay.cancelled.connect(self.on_snip_cancelled)

        self.snip_mode_target = "record"  # "record" or "screenshot"
        self.latest_screenshot_info = None
        self._force_quit = False
        self._has_shown_tray_hint = False

        self._setup_tray_icon()
        self._init_ui()
        self._connect_signals()
        self._load_settings_to_ui()
        self.refresh_gallery()

        # Register global hotkeys
        hotkey_manager.register_all()
        self._update_hotkey_status_label()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header Bar
        header = QWidget()
        header.setObjectName("headerWidget")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 12, 20, 12)

        # Logo & App Title
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        app_title = QLabel("ScreenRecorder Pro")
        app_title.setObjectName("appTitle")
        app_subtitle = QLabel("Ghi màn hình & Chụp ảnh siêu tốc bằng DXGI BetterCam")
        app_subtitle.setObjectName("appSubtitle")
        title_box.addWidget(app_title)
        title_box.addWidget(app_subtitle)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Status badge
        self.status_badge = QLabel("Sẵn sàng")
        self.status_badge.setObjectName("statusBadge")
        header_layout.addWidget(self.status_badge)

        # Top Action: Open Folder
        self.btn_open_folder = QPushButton("Mở thư mục")
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        header_layout.addWidget(self.btn_open_folder)

        # Top Action: Restart App Button
        self.btn_restart = QPushButton("Khởi động lại")
        self.btn_restart.setObjectName("restartBtn")
        self.btn_restart.setToolTip("Khởi động lại ứng dụng")
        self.btn_restart.clicked.connect(self.restart_app)
        header_layout.addWidget(self.btn_restart)

        # Top Action: Quit App Button
        self.btn_exit = QPushButton("Thoát hẳn")
        self.btn_exit.setObjectName("exitBtn")
        self.btn_exit.setToolTip("Thoát hoàn toàn ứng dụng (không chạy ngầm trong khay hệ thống)")
        self.btn_exit.clicked.connect(self.quit_app)
        header_layout.addWidget(self.btn_exit)

        main_layout.addWidget(header)

        # 2. Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setContentsMargins(15, 10, 15, 15)

        self.tab_record = self._create_record_tab()
        self.tab_screenshot = self._create_screenshot_tab()
        self.tab_gallery = self._create_gallery_tab()
        self.tab_hotkeys = self._create_hotkeys_tab()

        self.tabs.addTab(self.tab_record, "Ghi hình (Record)")
        self.tabs.addTab(self.tab_screenshot, "Chụp ảnh (Screenshot)")
        self.tabs.addTab(self.tab_gallery, "Thư viện (Gallery)")
        self.tabs.addTab(self.tab_hotkeys, "Phím tắt (Hotkeys)")

        main_layout.addWidget(self.tabs)

    def _create_record_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Control & Timer Card
        control_card = QFrame()
        control_card.setProperty("class", "card")
        control_layout = QVBoxLayout(control_card)

        # Timer & Pulse indicator
        timer_row = QHBoxLayout()
        self.pulse_dot = PulsingDot()
        self.label_timer = QLabel("00:00:00")
        self.label_timer.setObjectName("timerLabel")
        timer_row.addWidget(self.pulse_dot)
        timer_row.addWidget(self.label_timer)
        timer_row.addStretch()

        # Big Action buttons
        self.btn_record = QPushButton("BẮT ĐẦU GHI HÌNH")
        self.btn_record.setObjectName("recordBtn")
        self.btn_record.clicked.connect(self.toggle_recording)

        self.btn_pause = QPushButton("Tạm dừng")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.toggle_pause)

        timer_row.addWidget(self.btn_pause)
        timer_row.addWidget(self.btn_record)
        control_layout.addLayout(timer_row)

        layout.addWidget(control_card)

        # Stat cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        self.stat_fps = StatCard("Framerate thực tế", "-- FPS")
        self.stat_frames = StatCard("Tổng số khung hình", "0 frames")
        self.stat_resolution = StatCard("Vùng ghi hình", "Toàn màn hình")
        self.stat_time = StatCard("Thời gian đã ghi", "0.0s")

        stats_row.addWidget(self.stat_fps)
        stats_row.addWidget(self.stat_frames)
        stats_row.addWidget(self.stat_resolution)
        stats_row.addWidget(self.stat_time)
        layout.addLayout(stats_row)

        # Settings Card
        settings_card = QFrame()
        settings_card.setProperty("class", "card")
        settings_layout = QGridLayout(settings_card)
        settings_layout.setContentsMargins(16, 16, 16, 16)
        settings_layout.setHorizontalSpacing(16)
        settings_layout.setVerticalSpacing(12)

        # Row 0: Capture area mode
        settings_layout.addWidget(QLabel("Khu vực ghi hình:"), 0, 0)
        area_box = QHBoxLayout()
        self.combo_area = QComboBox()
        self.combo_area.addItems(["Toàn màn hình (Full Screen)", "Vùng chọn tùy chỉnh (Select Area)"])
        self.combo_area.currentIndexChanged.connect(self.on_area_mode_changed)
        self.btn_select_snip = QPushButton("Chọn vùng...")
        self.btn_select_snip.setEnabled(False)
        self.btn_select_snip.clicked.connect(self.start_snip_for_record)
        area_box.addWidget(self.combo_area, 2)
        area_box.addWidget(self.btn_select_snip, 1)
        settings_layout.addLayout(area_box, 0, 1)

        # Row 1: Target FPS & Quality
        settings_layout.addWidget(QLabel("Tần số quét (Framerate):"), 1, 0)
        fps_box = QHBoxLayout()
        self.combo_fps = QComboBox()
        self.combo_fps.addItems(["60 FPS (Mượt mà nhất - Khuyên dùng)", "30 FPS (Tiêu chuẩn)", "120 FPS (Tốc độ cao)"])
        self.combo_fps.currentIndexChanged.connect(self.on_setting_changed)
        fps_box.addWidget(self.combo_fps)
        settings_layout.addLayout(fps_box, 1, 1)

        settings_layout.addWidget(QLabel("Chất lượng video:"), 2, 0)
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["Chuẩn nét (CRF 22 - Cân bằng)", "Siêu nét (CRF 18 - Rất cao)", "Tiết kiệm (CRF 26 - Nhẹ)"])
        self.combo_quality.currentIndexChanged.connect(self.on_setting_changed)
        settings_layout.addWidget(self.combo_quality, 2, 1)

        # Row 3: Video Hardware Encoder
        settings_layout.addWidget(QLabel("Bộ mã hóa (GPU/CPU):"), 3, 0)
        self.combo_encoder = QComboBox()
        self.combo_encoder.addItem("Tự động (GPU Tăng tốc phần cứng - Khuyên dùng)", "auto")
        self.combo_encoder.addItem("AMD AMF (Card AMD Radeon)", "h264_amf")
        self.combo_encoder.addItem("Windows MediaFoundation (GPU chuẩn Windows)", "h264_mf")
        self.combo_encoder.addItem("NVIDIA NVENC (Card NVIDIA)", "h264_nvenc")
        self.combo_encoder.addItem("CPU Phần mềm (libx264 - Nặng CPU)", "libx264")
        self.combo_encoder.currentIndexChanged.connect(self.on_setting_changed)
        settings_layout.addWidget(self.combo_encoder, 3, 1)

        # Row 4: Monitor
        settings_layout.addWidget(QLabel("Màn hình hiển thị:"), 4, 0)
        self.combo_monitor = QComboBox()
        self._refresh_monitors()
        self.combo_monitor.currentIndexChanged.connect(self.on_setting_changed)
        settings_layout.addWidget(self.combo_monitor, 4, 1)

        # Row 5: Cursor
        settings_layout.addWidget(QLabel("Con trỏ chuột:"), 5, 0)
        self.chk_cursor = QCheckBox("Ghi lại con trỏ chuột trên màn hình")
        self.chk_cursor.setChecked(True)
        self.chk_cursor.stateChanged.connect(self.on_setting_changed)
        settings_layout.addWidget(self.chk_cursor, 5, 1)

        # Row 6: Audio recording & source
        settings_layout.addWidget(QLabel("Thu âm thanh:"), 6, 0)
        audio_box = QHBoxLayout()
        self.chk_audio = QCheckBox("Bật thu âm")
        self.chk_audio.setChecked(False)
        self.chk_audio.stateChanged.connect(self.on_audio_chk_changed)

        self.combo_audio_source = QComboBox()
        self.combo_audio_source.addItem("🔊 Âm thanh máy tính (Hệ thống / Ứng dụng)", "system")
        self.combo_audio_source.addItem("🎧 Cả Âm thanh máy tính + Microphone", "both")
        self.combo_audio_source.addItem("🎙️ Chỉ Microphone", "mic")
        self.combo_audio_source.setEnabled(False)
        self.combo_audio_source.currentIndexChanged.connect(self.on_audio_source_changed)

        audio_box.addWidget(self.chk_audio)
        audio_box.addWidget(self.combo_audio_source, 1)
        settings_layout.addLayout(audio_box, 6, 1)

        # Row 7: Specific audio device
        self.label_audio_dev = QLabel("Thiết bị âm thanh:")
        settings_layout.addWidget(self.label_audio_dev, 7, 0)
        self.combo_audio_dev = QComboBox()
        self.combo_audio_dev.setEnabled(False)
        self._refresh_audio_devices()
        self.combo_audio_dev.currentIndexChanged.connect(self.on_setting_changed)
        settings_layout.addWidget(self.combo_audio_dev, 7, 1)

        layout.addWidget(settings_card)
        layout.addStretch()
        return widget

    def _create_screenshot_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Action bar
        act_card = QFrame()
        act_card.setProperty("class", "card")
        act_layout = QHBoxLayout(act_card)

        self.btn_snap_full = QPushButton("Chụp toàn màn hình")
        self.btn_snap_full.setObjectName("primaryBtn")
        self.btn_snap_full.clicked.connect(self.take_full_screenshot)

        self.btn_snap_area = QPushButton("Chụp vùng chọn (Snipping)")
        self.btn_snap_area.setObjectName("successBtn")
        self.btn_snap_area.clicked.connect(self.start_snip_for_screenshot)

        self.chk_snap_cursor = QCheckBox("Bao gồm con trỏ chuột")
        self.chk_snap_clipboard = QCheckBox("Tự động sao chép Clipboard (Ctrl + V)")
        self.chk_snap_clipboard.setChecked(True)

        act_layout.addWidget(self.btn_snap_full)
        act_layout.addWidget(self.btn_snap_area)
        act_layout.addSpacing(20)
        act_layout.addWidget(self.chk_snap_cursor)
        act_layout.addWidget(self.chk_snap_clipboard)
        act_layout.addStretch()

        layout.addWidget(act_card)

        # Preview card
        preview_card = QFrame()
        preview_card.setProperty("class", "card")
        prev_layout = QVBoxLayout(preview_card)

        prev_header = QHBoxLayout()
        self.label_preview_title = QLabel("Xem trước ảnh vừa chụp")
        self.label_preview_title.setStyleSheet("font-weight: 700; color: #cbd5e1;")
        self.label_preview_meta = QLabel("Chưa chụp ảnh nào trong phiên này")
        self.label_preview_meta.setStyleSheet("color: #94a3b8; font-size: 12px;")
        prev_header.addWidget(self.label_preview_title)
        prev_header.addStretch()
        prev_header.addWidget(self.label_preview_meta)
        prev_layout.addLayout(prev_header)

        # Image view
        self.preview_image_label = QLabel("Hình ảnh xem trước sẽ hiển thị tại đây")
        self.preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_label.setStyleSheet("""
            background-color: #0f172a;
            border: 1px dashed #334155;
            border-radius: 8px;
            color: #64748b;
            min-height: 320px;
        """)
        prev_layout.addWidget(self.preview_image_label)

        # Quick action buttons for screenshot
        btn_row = QHBoxLayout()
        self.btn_open_image = QPushButton("Mở ảnh")
        self.btn_open_image.setEnabled(False)
        self.btn_open_image.clicked.connect(self.open_current_screenshot)

        self.btn_copy_image = QPushButton("Sao chép ảnh vào Clipboard")
        self.btn_copy_image.setEnabled(False)
        self.btn_copy_image.clicked.connect(self.copy_current_screenshot)

        self.btn_open_img_folder = QPushButton("Mở thư mục ảnh")
        self.btn_open_img_folder.clicked.connect(lambda: self._open_dir(config.get("save_dir_screenshot")))

        btn_row.addWidget(self.btn_open_image)
        btn_row.addWidget(self.btn_copy_image)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_open_img_folder)
        prev_layout.addLayout(btn_row)

        layout.addWidget(preview_card)
        return widget

    def _create_gallery_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Filter and refresh
        top_row = QHBoxLayout()
        self.combo_gallery_filter = QComboBox()
        self.combo_gallery_filter.addItems(["Tất cả tệp (Video & Ảnh)", "Chỉ Video (.mp4)", "Chỉ Ảnh chụp (.png)"])
        self.combo_gallery_filter.currentIndexChanged.connect(self.refresh_gallery)

        btn_refresh = QPushButton("Làm mới")
        btn_refresh.clicked.connect(self.refresh_gallery)

        btn_open_video_folder = QPushButton("Mở thư mục Video")
        btn_open_video_folder.clicked.connect(lambda: self._open_dir(config.get("save_dir_video")))

        btn_open_snap_folder = QPushButton("Mở thư mục Ảnh")
        btn_open_snap_folder.clicked.connect(lambda: self._open_dir(config.get("save_dir_screenshot")))

        top_row.addWidget(QLabel("Bộ lọc:"))
        top_row.addWidget(self.combo_gallery_filter)
        top_row.addWidget(btn_refresh)
        top_row.addStretch()
        top_row.addWidget(btn_open_video_folder)
        top_row.addWidget(btn_open_snap_folder)
        layout.addLayout(top_row)

        # List widget
        self.gallery_list = QListWidget()
        self.gallery_list.itemDoubleClicked.connect(self.on_gallery_item_double_clicked)
        layout.addWidget(self.gallery_list)

        hint = QLabel("Nhấp đúp vào tệp để mở trực tiếp trong ứng dụng Windows mặc định")
        hint.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(hint)

        return widget

    def _create_hotkeys_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)

        # Master toggle
        top_row = QHBoxLayout()
        self.chk_enable_hotkeys = QCheckBox("Kích hoạt phím tắt toàn hệ thống (Global Hotkeys)")
        self.chk_enable_hotkeys.setStyleSheet("font-weight: 700; font-size: 14px; color: #38bdf8;")
        self.chk_enable_hotkeys.setChecked(config.get("hotkeys_enabled", True))
        self.chk_enable_hotkeys.stateChanged.connect(self.on_toggle_hotkeys_master)
        top_row.addWidget(self.chk_enable_hotkeys)
        top_row.addStretch()

        # Preset selector
        top_row.addWidget(QLabel("Bộ mẫu phím tắt:"))
        self.combo_hotkey_preset = QComboBox()
        self.combo_hotkey_preset.addItems([
            "Mặc định (F9 / F10 / F11 / F12)",
            "Tổ hợp Ctrl (Ctrl+F9 / Ctrl+F10 / Ctrl+F11 / Ctrl+F12)",
            "Tổ hợp Alt (Alt+1 / Alt+2 / Alt+3 / Alt+4)"
        ])
        self.combo_hotkey_preset.currentIndexChanged.connect(self.on_hotkey_preset_changed)
        top_row.addWidget(self.combo_hotkey_preset)
        card_layout.addLayout(top_row)

        # Grid of hotkey bindings
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)

        grid.addWidget(QLabel("Bắt đầu / Dừng ghi hình:"), 0, 0)
        self.txt_hotkey_record = QLineEdit()
        self.txt_hotkey_record.setPlaceholderText("VD: F9, Ctrl+F9")
        grid.addWidget(self.txt_hotkey_record, 0, 1)

        grid.addWidget(QLabel("Tạm dừng / Tiếp tục ghi:"), 1, 0)
        self.txt_hotkey_pause = QLineEdit()
        self.txt_hotkey_pause.setPlaceholderText("VD: F10, Ctrl+F10")
        grid.addWidget(self.txt_hotkey_pause, 1, 1)

        grid.addWidget(QLabel("Chụp toàn màn hình:"), 2, 0)
        self.txt_hotkey_snap_full = QLineEdit()
        self.txt_hotkey_snap_full.setPlaceholderText("VD: F11, Ctrl+F11")
        grid.addWidget(self.txt_hotkey_snap_full, 2, 1)

        grid.addWidget(QLabel("Chụp vùng chọn (Snipping):"), 3, 0)
        self.txt_hotkey_snap_snip = QLineEdit()
        self.txt_hotkey_snap_snip.setPlaceholderText("VD: F12, Ctrl+F12")
        grid.addWidget(self.txt_hotkey_snap_snip, 3, 1)

        card_layout.addLayout(grid)

        # Buttons row
        btn_row = QHBoxLayout()
        self.btn_save_hotkeys = QPushButton("Lưu & Áp dụng phím tắt")
        self.btn_save_hotkeys.setObjectName("primaryBtn")
        self.btn_save_hotkeys.clicked.connect(self.apply_hotkeys)

        self.btn_reset_hotkeys = QPushButton("Đặt lại mặc định")
        self.btn_reset_hotkeys.clicked.connect(self.reset_hotkeys_to_default)

        btn_row.addWidget(self.btn_save_hotkeys)
        btn_row.addWidget(self.btn_reset_hotkeys)
        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        # Status note
        self.label_hotkey_status = QLabel("")
        self.label_hotkey_status.setStyleSheet("color: #10b981; font-weight: 600; font-size: 12px;")
        card_layout.addWidget(self.label_hotkey_status)

        layout.addWidget(card)

        # Guide card
        guide_card = QFrame()
        guide_card.setProperty("class", "card")
        guide_layout = QVBoxLayout(guide_card)
        guide_title = QLabel("📌 Hướng dẫn sử dụng Phím tắt Toàn cục")
        guide_title.setStyleSheet("font-weight: 700; color: #cbd5e1;")
        guide_text = QLabel(
            "• Phím tắt toàn cục hoạt động ngay cả khi ứng dụng đang ẩn dưới thanh Taskbar hoặc bạn đang chơi game, lướt web.\n"
            "• Bạn có thể dùng phím đơn (F1 đến F12) hoặc tổ hợp phím (Ctrl+F9, Alt+Shift+S, ...).\n"
            "• Bấm 'Lưu & Áp dụng' để hệ thống đăng ký phím tắt mới ngay lập tức."
        )
        guide_text.setStyleSheet("color: #94a3b8; line-height: 1.5;")
        guide_layout.addWidget(guide_title)
        guide_layout.addWidget(guide_text)
        layout.addWidget(guide_card)

        layout.addStretch()
        return widget

    def _connect_signals(self):
        # Recorder signals
        recorder.sig_started.connect(self.on_record_started)
        recorder.sig_tick.connect(self.on_record_tick)
        recorder.sig_paused.connect(self.on_record_paused)
        recorder.sig_resumed.connect(self.on_record_resumed)
        recorder.sig_stopped.connect(self.on_record_stopped)
        recorder.sig_error.connect(self.on_record_error)

        # Global Hotkey signals
        hotkey_manager.sig_record_toggle.connect(self.toggle_recording)
        hotkey_manager.sig_record_pause.connect(self.toggle_pause)
        hotkey_manager.sig_screenshot_full.connect(self.take_full_screenshot)
        hotkey_manager.sig_screenshot_snip.connect(self.start_snip_for_screenshot)

    def _refresh_monitors(self):
        self.combo_monitor.clear()
        monitors = capture_engine.get_monitors()
        for m in monitors:
            self.combo_monitor.addItem(f"{m['name']} - {m['details']}", m['index'])

    def _refresh_audio_devices(self):
        source = getattr(self, "combo_audio_source", None)
        src_val = source.currentData() if source else "system"

        self.combo_audio_dev.blockSignals(True)
        self.combo_audio_dev.clear()

        if src_val == "system":
            if hasattr(self, "label_audio_dev"):
                self.label_audio_dev.setText("Loa / Thiết bị phát:")
            self.combo_audio_dev.addItem("Loa / Tai nghe hệ thống mặc định", None)
            sys_devs = self.audio_recorder_helper.get_system_devices()
            for d in sys_devs:
                label = f"{d['name']} {'(Mặc định)' if d['is_default'] else ''}".strip()
                self.combo_audio_dev.addItem(label, d['index'])
        elif src_val == "mic":
            if hasattr(self, "label_audio_dev"):
                self.label_audio_dev.setText("Microphone:")
            self.combo_audio_dev.addItem("Microphone hệ thống mặc định", None)
            mic_devs = self.audio_recorder_helper.get_mic_devices()
            for d in mic_devs:
                label = f"{d['name']} {'(Mặc định)' if d['is_default'] else ''}".strip()
                self.combo_audio_dev.addItem(label, d['index'])
        else:  # "both"
            if hasattr(self, "label_audio_dev"):
                self.label_audio_dev.setText("Microphone kết hợp:")
            self.combo_audio_dev.addItem("Microphone mặc định (Hòa âm cùng Loa máy tính)", None)
            mic_devs = self.audio_recorder_helper.get_mic_devices()
            for d in mic_devs:
                label = f"{d['name']} (Hòa âm cùng Loa)".strip()
                self.combo_audio_dev.addItem(label, d['index'])

        self.combo_audio_dev.blockSignals(False)

    def on_audio_source_changed(self, index):
        self._refresh_audio_devices()
        self.on_setting_changed()

    def _load_settings_to_ui(self):
        fps = config.get("fps", 60)
        if fps == 60:
            self.combo_fps.setCurrentIndex(0)
        elif fps == 30:
            self.combo_fps.setCurrentIndex(1)
        elif fps == 120:
            self.combo_fps.setCurrentIndex(2)

        quality = config.get("quality", "medium")
        if quality == "medium":
            self.combo_quality.setCurrentIndex(0)
        elif quality == "high":
            self.combo_quality.setCurrentIndex(1)
        elif quality == "low":
            self.combo_quality.setCurrentIndex(2)

        encoder_val = config.get("encoder", "auto")
        for i in range(self.combo_encoder.count()):
            if self.combo_encoder.itemData(i) == encoder_val:
                self.combo_encoder.setCurrentIndex(i)
                break

        # Load audio source
        audio_src = config.get("audio_source", "system")
        for i in range(self.combo_audio_source.count()):
            if self.combo_audio_source.itemData(i) == audio_src:
                self.combo_audio_source.setCurrentIndex(i)
                break

        self._refresh_audio_devices()

        self.chk_cursor.setChecked(config.get("record_cursor", True))
        audio_on = config.get("record_audio", False)
        self.chk_audio.setChecked(audio_on)
        self.combo_audio_source.setEnabled(audio_on)
        self.combo_audio_dev.setEnabled(audio_on)

        # Load hotkeys
        self.txt_hotkey_record.setText(config.get("hotkey_record_toggle", "F9"))
        self.txt_hotkey_pause.setText(config.get("hotkey_record_pause", "F10"))
        self.txt_hotkey_snap_full.setText(config.get("hotkey_screenshot_full", "F11"))
        self.txt_hotkey_snap_snip.setText(config.get("hotkey_screenshot_snip", "F12"))
        self.chk_enable_hotkeys.setChecked(config.get("hotkeys_enabled", True))

    def on_toggle_hotkeys_master(self, state):
        enabled = bool(state == Qt.CheckState.Checked.value or state == 2 or state is True)
        config.set("hotkeys_enabled", enabled)
        if enabled:
            hotkey_manager.register_all()
        else:
            hotkey_manager.unregister_all()
        self._update_hotkey_status_label()

    def on_hotkey_preset_changed(self, idx):
        if idx == 0:  # Default
            self.txt_hotkey_record.setText("F9")
            self.txt_hotkey_pause.setText("F10")
            self.txt_hotkey_snap_full.setText("F11")
            self.txt_hotkey_snap_snip.setText("F12")
        elif idx == 1:  # Ctrl+
            self.txt_hotkey_record.setText("Ctrl+F9")
            self.txt_hotkey_pause.setText("Ctrl+F10")
            self.txt_hotkey_snap_full.setText("Ctrl+F11")
            self.txt_hotkey_snap_snip.setText("Ctrl+F12")
        elif idx == 2:  # Alt+
            self.txt_hotkey_record.setText("Alt+1")
            self.txt_hotkey_pause.setText("Alt+2")
            self.txt_hotkey_snap_full.setText("Alt+3")
            self.txt_hotkey_snap_snip.setText("Alt+4")

    def apply_hotkeys(self):
        config.set("hotkeys_enabled", self.chk_enable_hotkeys.isChecked())
        config.set("hotkey_record_toggle", self.txt_hotkey_record.text().strip())
        config.set("hotkey_record_pause", self.txt_hotkey_pause.text().strip())
        config.set("hotkey_screenshot_full", self.txt_hotkey_snap_full.text().strip())
        config.set("hotkey_screenshot_snip", self.txt_hotkey_snap_snip.text().strip())

        success = hotkey_manager.reload()
        self._update_hotkey_status_label()
        if success:
            QMessageBox.information(self, "Thành công", "Đã cập nhật và kích hoạt phím tắt toàn cục thành công!")
        else:
            QMessageBox.warning(self, "Lưu ý", "Đã cập nhật phím tắt. Một số phím tắt có thể bị trùng hoặc không thể gán.")

    def reset_hotkeys_to_default(self):
        self.txt_hotkey_record.setText("F9")
        self.txt_hotkey_pause.setText("F10")
        self.txt_hotkey_snap_full.setText("F11")
        self.txt_hotkey_snap_snip.setText("F12")
        self.chk_enable_hotkeys.setChecked(True)
        self.apply_hotkeys()

    def _update_hotkey_status_label(self):
        if not config.get("hotkeys_enabled", True):
            self.label_hotkey_status.setText("⚠️ Phím tắt toàn cục hiện đang TẮT.")
            self.label_hotkey_status.setStyleSheet("color: #f59e0b; font-weight: 600; font-size: 12px;")
        else:
            k1 = config.get("hotkey_record_toggle", "F9")
            k2 = config.get("hotkey_record_pause", "F10")
            k3 = config.get("hotkey_screenshot_full", "F11")
            k4 = config.get("hotkey_screenshot_snip", "F12")
            self.label_hotkey_status.setText(f"✓ Đang kích hoạt: {k1} (Ghi hình) | {k2} (Tạm dừng) | {k3} (Chụp toàn màn hình) | {k4} (Chụp vùng)")
            self.label_hotkey_status.setStyleSheet("color: #10b981; font-weight: 600; font-size: 12px;")

    def on_setting_changed(self):
        fps_map = {0: 60, 1: 30, 2: 120}
        config.set("fps", fps_map.get(self.combo_fps.currentIndex(), 60))

        quality_map = {0: "medium", 1: "high", 2: "low"}
        config.set("quality", quality_map.get(self.combo_quality.currentIndex(), "medium"))

        enc_val = self.combo_encoder.currentData() or "auto"
        config.set("encoder", enc_val)

        config.set("record_cursor", self.chk_cursor.isChecked())
        config.set("record_audio", self.chk_audio.isChecked())
        if hasattr(self, "combo_audio_source"):
            config.set("audio_source", self.combo_audio_source.currentData() or "system")

    def on_audio_chk_changed(self, state):
        audio_on = self.chk_audio.isChecked()
        if hasattr(self, "combo_audio_source"):
            self.combo_audio_source.setEnabled(audio_on)
        self.combo_audio_dev.setEnabled(audio_on)
        self.on_setting_changed()

    def on_area_mode_changed(self, index):
        if index == 1:
            self.btn_select_snip.setEnabled(True)
            self.start_snip_for_record()
        else:
            self.btn_select_snip.setEnabled(False)
            self.custom_region = None
            self.stat_resolution.set_value("Toàn màn hình")

    def start_snip_for_record(self):
        self.snip_mode_target = "record"
        self.snip_overlay.show_fullscreen_snip()

    def start_snip_for_screenshot(self):
        self.snip_mode_target = "screenshot"
        self.snip_overlay.show_fullscreen_snip()

    @Slot(tuple)
    def on_region_selected(self, region):
        l, t, r, b = region
        w = r - l
        h = b - t
        if self.snip_mode_target == "record":
            self.custom_region = region
            self.stat_resolution.set_value(f"{w} × {h}")
            self.combo_area.setCurrentIndex(1)
        elif self.snip_mode_target == "screenshot":
            self._do_screenshot(region=region)

    @Slot()
    def on_snip_cancelled(self):
        if self.snip_mode_target == "record" and self.custom_region is None:
            self.combo_area.setCurrentIndex(0)
            self.stat_resolution.set_value("Toàn màn hình")

    def take_full_screenshot(self):
        self._do_screenshot(region=None)

    def _do_screenshot(self, region=None):
        try:
            cur_mon = self.combo_monitor.currentData() or 0
            include_cur = self.chk_snap_cursor.isChecked()
            copy_clip = self.chk_snap_clipboard.isChecked()

            result = capture_engine.capture_screenshot(
                monitor_idx=cur_mon,
                region=region,
                include_cursor=include_cur,
                copy_to_clipboard=copy_clip
            )

            self.latest_screenshot_info = result
            # Display preview
            pixmap = QPixmap.fromImage(result["qimage"])
            scaled_pixmap = pixmap.scaled(
                self.preview_image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_image_label.setPixmap(scaled_pixmap)

            size_kb = result["size_bytes"] / 1024
            meta_str = f"Độ phân giải: {result['width']}×{result['height']} | Dung lượng: {size_kb:.1f} KB | {result['filename']}"
            if copy_clip:
                meta_str += " (Đã chép vào Clipboard)"
            self.label_preview_meta.setText(meta_str)

            self.btn_open_image.setEnabled(True)
            self.btn_copy_image.setEnabled(True)
            self.refresh_gallery()

        except Exception as e:
            QMessageBox.critical(self, "Lỗi chụp màn hình", f"Không thể chụp màn hình: {str(e)}")

    def open_current_screenshot(self):
        if self.latest_screenshot_info and os.path.exists(self.latest_screenshot_info["path"]):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.latest_screenshot_info["path"]))

    def copy_current_screenshot(self):
        if self.latest_screenshot_info and "qimage" in self.latest_screenshot_info:
            QGuiApplication.clipboard().setImage(self.latest_screenshot_info["qimage"])
            self.label_preview_meta.setText(self.label_preview_meta.text() + " [Đã copy!]")

    def toggle_recording(self):
        if not recorder.is_recording:
            # Start
            fps_map = {0: 60, 1: 30, 2: 120}
            fps = fps_map.get(self.combo_fps.currentIndex(), 60)

            quality_map = {0: "medium", 1: "high", 2: "low"}
            quality = quality_map.get(self.combo_quality.currentIndex(), "medium")

            encoder_val = self.combo_encoder.currentData() or "auto"
            mon_idx = self.combo_monitor.currentData() or 0
            rec_cur = self.chk_cursor.isChecked()
            rec_aud = self.chk_audio.isChecked()
            aud_src = self.combo_audio_source.currentData() or "system"
            aud_dev = self.combo_audio_dev.currentData() if rec_aud else None
            sys_dev = aud_dev if aud_src == "system" else None
            mic_dev = aud_dev if aud_src in ("mic", "both") else None

            success = recorder.start_recording(
                monitor_idx=mon_idx,
                region=self.custom_region,
                fps=fps,
                quality=quality,
                encoder=encoder_val,
                record_cursor=rec_cur,
                record_audio=rec_aud,
                audio_source=aud_src,
                audio_device_system=sys_dev,
                audio_device_mic=mic_dev
            )
            if not success:
                QMessageBox.warning(self, "Cảnh báo", "Không thể bắt đầu ghi hình. Vui lòng kiểm tra lại thiết bị!")
        else:
            # Stop
            self.btn_record.setEnabled(False)
            self.btn_record.setText("Đang xuất video...")
            recorder.stop_recording()

    def toggle_pause(self):
        if not recorder.is_recording:
            return
        if recorder.is_paused:
            recorder.resume_recording()
        else:
            recorder.pause_recording()

    @Slot(str)
    def on_record_started(self, output_path):
        self.btn_record.setEnabled(True)
        self.btn_record.setText("DỪNG GHI HÌNH")
        self.btn_record.setProperty("recording", "true")
        self.btn_record.style().unpolish(self.btn_record)
        self.btn_record.style().polish(self.btn_record)

        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("Tạm dừng")

        enc_names = {
            "h264_amf": "GPU AMD AMF",
            "h264_mf": "GPU MediaFoundation",
            "h264_nvenc": "GPU NVIDIA NVENC",
            "h264_qsv": "GPU Intel QSV",
            "libx264": "CPU libx264"
        }
        enc_disp = enc_names.get(recorder.active_encoder, recorder.active_encoder or "GPU")
        self.status_badge.setText(f"Đang ghi ({enc_disp})")
        self.status_badge.setProperty("recording", "true")
        self.status_badge.setProperty("paused", "false")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

        self.pulse_dot.start()
        self.combo_area.setEnabled(False)
        self.btn_select_snip.setEnabled(False)
        self.combo_fps.setEnabled(False)
        self.combo_quality.setEnabled(False)
        self.combo_encoder.setEnabled(False)
        self.combo_monitor.setEnabled(False)
        self.chk_audio.setEnabled(False)
        self.combo_audio_source.setEnabled(False)
        self.combo_audio_dev.setEnabled(False)
        self.chk_cursor.setEnabled(False)

    @Slot(float, float, int)
    def on_record_tick(self, duration_sec, current_fps, frame_count):
        # Format duration HH:MM:SS
        m, s = divmod(int(duration_sec), 60)
        h, m = divmod(m, 60)
        self.label_timer.setText(f"{h:02d}:{m:02d}:{s:02d}")

        self.stat_fps.set_value(f"{current_fps:.1f} FPS")
        self.stat_frames.set_value(f"{frame_count:,} frames")
        self.stat_time.set_value(f"{duration_sec:.1f}s")

    @Slot()
    def on_record_paused(self):
        self.btn_pause.setText("Tiếp tục ghi")
        self.status_badge.setText("Đã tạm dừng")
        self.status_badge.setProperty("paused", "true")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.pulse_dot.stop()

    @Slot()
    def on_record_resumed(self):
        self.btn_pause.setText("Tạm dừng")
        enc_names = {
            "h264_amf": "GPU AMD AMF",
            "h264_mf": "GPU MediaFoundation",
            "h264_nvenc": "GPU NVIDIA NVENC",
            "h264_qsv": "GPU Intel QSV",
            "libx264": "CPU libx264"
        }
        enc_disp = enc_names.get(recorder.active_encoder, recorder.active_encoder or "GPU")
        self.status_badge.setText(f"Đang ghi ({enc_disp})")
        self.status_badge.setProperty("paused", "false")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.pulse_dot.start()

    @Slot(str, float, int, int)
    def on_record_stopped(self, output_path, duration_sec, frame_count, file_size_bytes):
        self.btn_record.setEnabled(True)
        self.btn_record.setText("BẮT ĐẦU GHI HÌNH")
        self.btn_record.setProperty("recording", "false")
        self.btn_record.style().unpolish(self.btn_record)
        self.btn_record.style().polish(self.btn_record)

        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("Tạm dừng")

        self.status_badge.setText("Sẵn sàng")
        self.status_badge.setProperty("recording", "false")
        self.status_badge.setProperty("paused", "false")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

        self.pulse_dot.stop()
        self.label_timer.setText("00:00:00")

        self.combo_area.setEnabled(True)
        self.btn_select_snip.setEnabled(self.combo_area.currentIndex() == 1)
        self.combo_fps.setEnabled(True)
        self.combo_quality.setEnabled(True)
        self.combo_encoder.setEnabled(True)
        self.combo_monitor.setEnabled(True)
        self.chk_audio.setEnabled(True)
        audio_on = self.chk_audio.isChecked()
        self.combo_audio_source.setEnabled(audio_on)
        self.combo_audio_dev.setEnabled(audio_on)
        self.chk_cursor.setEnabled(True)

        self.refresh_gallery()

        size_mb = file_size_bytes / (1024 * 1024)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Ghi hình hoàn tất!")
        msg_box.setText(f"Video đã được lưu thành công!\n\nThời lượng: {duration_sec:.1f}s\nSố khung hình: {frame_count}\nDung lượng: {size_mb:.2f} MB\n\nĐường dẫn: {output_path}")
        btn_open = msg_box.addButton("Mở Video", QMessageBox.ButtonRole.ActionRole)
        btn_folder = msg_box.addButton("Mở Thư Mục", QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton("Đóng", QMessageBox.ButtonRole.RejectRole)
        msg_box.exec()

        if msg_box.clickedButton() == btn_open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_path))
        elif msg_box.clickedButton() == btn_folder:
            self._open_dir(os.path.dirname(output_path))

    @Slot(str)
    def on_record_error(self, err_msg):
        self.on_record_stopped("", 0, 0, 0)
        QMessageBox.critical(self, "Lỗi ghi hình", f"Đã xảy ra lỗi trong quá trình ghi hình:\n{err_msg}")

    def refresh_gallery(self):
        self.gallery_list.clear()
        filter_idx = self.combo_gallery_filter.currentIndex()

        video_dir = config.get("save_dir_video")
        snap_dir = config.get("save_dir_screenshot")

        items = []
        if filter_idx in (0, 1) and os.path.exists(video_dir):
            for f in os.listdir(video_dir):
                if f.lower().endswith(".mp4"):
                    p = os.path.join(video_dir, f)
                    items.append((os.path.getmtime(p), p, "VIDEO"))

        if filter_idx in (0, 2) and os.path.exists(snap_dir):
            for f in os.listdir(snap_dir):
                if f.lower().endswith((".png", ".jpg", ".webp")):
                    p = os.path.join(snap_dir, f)
                    items.append((os.path.getmtime(p), p, "IMAGE"))

        # Sort newest first
        items.sort(key=lambda x: x[0], reverse=True)

        for mtime, path, ftype in items:
            dt_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            sz_mb = os.path.getsize(path) / (1024 * 1024)
            icon_tag = "🎬 [VIDEO]" if ftype == "VIDEO" else "📷 [ẢNH]"
            text = f"{icon_tag}  {os.path.basename(path)}  |  {sz_mb:.2f} MB  |  {dt_str}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.gallery_list.addItem(item)

    def on_gallery_item_double_clicked(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def open_output_folder(self):
        current_tab = self.tabs.currentIndex()
        if current_tab == 1:
            self._open_dir(config.get("save_dir_screenshot"))
        else:
            self._open_dir(config.get("save_dir_video"))

    def _open_dir(self, dir_path):
        if os.path.exists(dir_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(dir_path))
        else:
            os.makedirs(dir_path, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(dir_path))

    def _setup_tray_icon(self):
        """Setup Windows System Tray Icon with menu and notification."""
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        self.tray_icon.setToolTip("ScreenRecorder Pro - BetterCam DXGI")

        tray_menu = QMenu(self)
        act_show = tray_menu.addAction("Mở giao diện ScreenRecorder")
        act_show.triggered.connect(self.show_and_activate)

        tray_menu.addSeparator()

        act_record = tray_menu.addAction("Bắt đầu / Dừng ghi hình (F9)")
        act_record.triggered.connect(self.toggle_recording)

        act_snap_full = tray_menu.addAction("Chụp toàn màn hình (F11)")
        act_snap_full.triggered.connect(self.take_full_screenshot)

        act_snap_snip = tray_menu.addAction("Chụp vùng chọn (F12)")
        act_snap_snip.triggered.connect(self.start_snip_for_screenshot)

        tray_menu.addSeparator()

        act_folder = tray_menu.addAction("Mở thư mục lưu trữ")
        act_folder.triggered.connect(self.open_output_folder)

        tray_menu.addSeparator()

        act_quit = tray_menu.addAction("Thoát hẳn ứng dụng")
        act_quit.triggered.connect(self.quit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_and_activate()

    def show_and_activate(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event: QCloseEvent):
        """Hide to systray when user clicks [X], unless force_quit is requested."""
        if self._force_quit:
            # Clean shutdown
            try:
                self.tray_icon.hide()
            except Exception:
                pass
            hotkey_manager.unregister_all()
            try:
                if recorder.is_recording:
                    recorder.stop_recording()
                capture_engine.release()
            except Exception:
                pass
            event.accept()
        else:
            # Minimize to system tray
            event.ignore()
            self.hide()
            if not self._has_shown_tray_hint:
                self._has_shown_tray_hint = True
                self.tray_icon.showMessage(
                    "ScreenRecorder Pro",
                    "Ứng dụng đã được thu nhỏ vào khay hệ thống. Bấm F9 để ghi, F11 để chụp ảnh, hoặc nhấp vào icon để mở lại giao diện.",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000
                )

    def quit_app(self):
        """Completely exit the application without hiding to tray."""
        if recorder.is_recording:
            reply = QMessageBox.question(
                self,
                "Đang ghi hình!",
                "Đang trong quá trình ghi hình, bạn có chắc chắn muốn dừng và thoát hoàn toàn không?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._force_quit = True
        self.close()
        QGuiApplication.quit()

    def restart_app(self):
        """Cleanly restart the application."""
        reply = QMessageBox.question(
            self,
            "Khởi động lại ứng dụng",
            "Bạn có chắc chắn muốn khởi động lại ứng dụng không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._force_quit = True
            try:
                self.tray_icon.hide()
            except Exception:
                pass
            hotkey_manager.unregister_all()
            try:
                if recorder.is_recording:
                    recorder.stop_recording()
                capture_engine.release()
            except Exception:
                pass

            # Relaunch process cleanly without console window
            script_dir = os.path.dirname(os.path.dirname(__file__))
            pythonw_candidate = os.path.join(script_dir, ".venv", "Scripts", "pythonw.exe")
            python_exe = pythonw_candidate if os.path.exists(pythonw_candidate) else sys.executable
            main_script = os.path.abspath(os.path.join(script_dir, "main.py"))

            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            subprocess.Popen([python_exe, main_script], creationflags=creation_flags)

            # Exit current app
            QGuiApplication.quit()
