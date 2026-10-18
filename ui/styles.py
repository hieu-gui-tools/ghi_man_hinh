DARK_STYLESHEET = """
QMainWindow {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}

QWidget {
    color: #f8fafc;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

/* Header Area */
#headerWidget {
    background-color: #1e293b;
    border-bottom: 1px solid #334155;
    padding: 12px 20px;
}

#appTitle {
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
}

#appSubtitle {
    font-size: 12px;
    color: #94a3b8;
}

/* Status Badge */
#statusBadge {
    background-color: #334155;
    color: #38bdf8;
    border-radius: 12px;
    padding: 4px 14px;
    font-weight: 600;
    font-size: 12px;
}

#statusBadge[recording="true"] {
    background-color: rgba(239, 68, 68, 0.2);
    color: #f87171;
    border: 1px solid #ef4444;
}

#statusBadge[paused="true"] {
    background-color: rgba(245, 158, 11, 0.2);
    color: #fbbf24;
    border: 1px solid #f59e0b;
}

/* Tabs */
QTabWidget::pane {
    border: none;
    background-color: #0f172a;
}

QTabBar::tab {
    background-color: #1e293b;
    color: #94a3b8;
    padding: 10px 22px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
    font-size: 13px;
}

QTabBar::tab:selected {
    background-color: #334155;
    color: #ffffff;
    border-bottom: 2px solid #6366f1;
}

QTabBar::tab:hover:!selected {
    background-color: #273549;
    color: #cbd5e1;
}

/* Card Container */
.card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px;
}

.cardTitle {
    font-size: 14px;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 8px;
}

/* Buttons */
QPushButton {
    background-color: #334155;
    color: #ffffff;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #475569;
    border-color: #64748b;
}

QPushButton:pressed {
    background-color: #1e293b;
}

QPushButton:disabled {
    background-color: #1e293b;
    color: #64748b;
    border-color: #334155;
}

/* Primary Button */
QPushButton#primaryBtn {
    background-color: #4f46e5;
    border: 1px solid #6366f1;
    color: #ffffff;
}

QPushButton#primaryBtn:hover {
    background-color: #6366f1;
}

/* Danger / Record Button */
QPushButton#recordBtn {
    background-color: #dc2626;
    border: 1px solid #ef4444;
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    border-radius: 10px;
    padding: 12px 24px;
}

QPushButton#recordBtn:hover {
    background-color: #ef4444;
}

QPushButton#recordBtn[recording="true"] {
    background-color: #b91c1c;
    border: 2px solid #f87171;
}

/* Success Button */
QPushButton#successBtn {
    background-color: #059669;
    border: 1px solid #10b981;
    color: #ffffff;
}

QPushButton#successBtn:hover {
    background-color: #10b981;
}

/* Restart Button */
QPushButton#restartBtn {
    background-color: #2e1065;
    border: 1px solid #7c3aed;
    color: #c4b5fd;
    font-weight: 600;
}

QPushButton#restartBtn:hover {
    background-color: #4c1d95;
    color: #ffffff;
}

/* Exit Button */
QPushButton#exitBtn {
    background-color: #450a0a;
    border: 1px solid #dc2626;
    color: #fca5a5;
    font-weight: 600;
}

QPushButton#exitBtn:hover {
    background-color: #7f1d1d;
    color: #ffffff;
    border-color: #ef4444;
}

/* QMenu (Systray Context Menu) */
QMenu {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 8px 24px 8px 16px;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: #4f46e5;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #334155;
    margin: 4px 8px;
}

/* ComboBox */
QComboBox {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 22px;
}

QComboBox:hover {
    border-color: #6366f1;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    color: #f8fafc;
    selection-background-color: #4f46e5;
    selection-color: #ffffff;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
    font-weight: 500;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #0f172a;
}

QCheckBox::indicator:checked {
    background-color: #6366f1;
    border-color: #818cf8;
}

/* Timer Display */
#timerLabel {
    font-size: 32px;
    font-weight: 800;
    font-family: "Consolas", "Courier New", monospace;
    color: #ffffff;
}

/* Stat Value */
.statValue {
    font-size: 20px;
    font-weight: 700;
    color: #38bdf8;
    font-family: "Consolas", "Courier New", monospace;
}

.statLabel {
    font-size: 11px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
}

/* Scroll Area & List */
QScrollArea {
    border: none;
    background-color: transparent;
}

QListWidget {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 4px;
}

QListWidget::item {
    background-color: #1e293b;
    border-radius: 6px;
    padding: 10px;
    margin: 3px 0;
    border: 1px solid #334155;
}

QListWidget::item:hover {
    background-color: #273549;
    border-color: #475569;
}

QListWidget::item:selected {
    background-color: #334155;
    border-color: #6366f1;
}

/* Scrollbar */
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 8px;
    margin: 0;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""
