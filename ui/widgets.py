from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
)
from PySide6.QtCore import Qt, QTimer, Property
from PySide6.QtGui import QPainter, QColor, QBrush

class PulsingDot(QWidget):
    """Animated pulsing red LED dot for active recording status."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self._is_pulsing = False
        self._alpha = 255
        self._direction = -15

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def start(self):
        self._is_pulsing = True
        self.timer.start(50)
        self.update()

    def stop(self):
        self._is_pulsing = False
        self.timer.stop()
        self._alpha = 255
        self.update()

    def _tick(self):
        self._alpha += self._direction
        if self._alpha <= 70:
            self._alpha = 70
            self._direction = 15
        elif self._alpha >= 255:
            self._alpha = 255
            self._direction = -15
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._is_pulsing:
            # Outer glow
            glow_color = QColor(239, 68, 68, int(self._alpha * 0.4))
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(1, 1, 18, 18)

            # Core red dot
            core_color = QColor(239, 68, 68, self._alpha)
            painter.setBrush(QBrush(core_color))
            painter.drawEllipse(4, 4, 12, 12)
        else:
            # Inactive grey dot
            painter.setBrush(QBrush(QColor(100, 116, 139)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(5, 5, 10, 10)

class StatCard(QFrame):
    """Card displaying a single metric."""
    def __init__(self, title: str, initial_value: str = "--", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setStyleSheet("""
            QFrame#statCard {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.label_title = QLabel(title)
        self.label_title.setProperty("class", "statLabel")
        self.label_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase;")

        self.label_value = QLabel(initial_value)
        self.label_value.setProperty("class", "statValue")
        self.label_value.setStyleSheet("color: #38bdf8; font-size: 18px; font-weight: 700; font-family: monospace;")

        layout.addWidget(self.label_title)
        layout.addWidget(self.label_value)

    def set_value(self, text: str):
        self.label_value.setText(text)
