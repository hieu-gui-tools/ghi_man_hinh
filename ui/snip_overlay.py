from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QCursor

class SnipOverlay(QWidget):
    """
    Transparent fullscreen overlay that allows the user to click & drag
    a custom capture rectangle.
    """
    region_selected = Signal(tuple)  # (left, top, right, bottom)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        self.start_pos = None
        self.current_pos = None
        self.is_dragging = False

    def show_fullscreen_snip(self):
        # Cover all screens / virtual desktop
        screen_geo = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(screen_geo)
        self.start_pos = None
        self.current_pos = None
        self.is_dragging = False
        self.show()
        self.activateWindow()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.globalPosition().toPoint()
            self.current_pos = self.start_pos
            self.is_dragging = True
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.cancel_snip()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.current_pos = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            rect = self.get_selected_rect()
            if rect.width() >= 10 and rect.height() >= 10:
                # Region tuple: (left, top, right, bottom)
                region = (rect.left(), rect.top(), rect.right(), rect.bottom())
                self.hide()
                self.region_selected.emit(region)
            else:
                self.cancel_snip()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_snip()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            rect = self.get_selected_rect()
            if rect.width() >= 10 and rect.height() >= 10:
                region = (rect.left(), rect.top(), rect.right(), rect.bottom())
                self.hide()
                self.region_selected.emit(region)
            else:
                self.cancel_snip()
        super().keyPressEvent(event)

    def cancel_snip(self):
        self.hide()
        self.cancelled.emit()

    def get_selected_rect(self) -> QRect:
        if self.start_pos is None or self.current_pos is None:
            return QRect()
        # Relative to overlay widget
        p1 = self.mapFromGlobal(self.start_pos)
        p2 = self.mapFromGlobal(self.current_pos)
        return QRect(p1, p2).normalized()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw darkened background over whole area
        painter.fillRect(self.rect(), QColor(0, 0, 0, 140))

        if self.start_pos and self.current_pos:
            rect = self.get_selected_rect()
            if rect.isValid() and rect.width() > 0 and rect.height() > 0:
                # Clear selected rectangle so it looks bright/transparent
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                painter.fillRect(rect, Qt.GlobalColor.transparent)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

                # Draw selection border
                pen = QPen(QColor(99, 102, 241), 2, Qt.PenStyle.SolidLine)
                painter.setPen(pen)
                painter.drawRect(rect)

                # Draw dimension badge above or inside rect
                dim_text = f"{rect.width()} × {rect.height()}"
                painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                
                # Badge position
                badge_w = 110
                badge_h = 26
                badge_x = rect.left() + (rect.width() - badge_w) // 2
                badge_y = rect.top() - badge_h - 6
                if badge_y < 10:
                    badge_y = rect.bottom() + 8

                painter.setBrush(QBrush(QColor(15, 23, 42, 220)))
                painter.setPen(QPen(QColor(99, 102, 241), 1))
                painter.drawRoundedRect(badge_x, badge_y, badge_w, badge_h, 6, 6)

                painter.setPen(QColor(255, 255, 255))
                painter.drawText(QRect(badge_x, badge_y, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, dim_text)
