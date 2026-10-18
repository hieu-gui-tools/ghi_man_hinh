import sys
import os
import ctypes

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# First: ensure default desktop and high DPI awareness before any COM/DirectX calls
from core.desktop_utils import ensure_default_desktop, enable_dpi_awareness
enable_dpi_awareness()
ensure_default_desktop()

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from ui.main_window import MainWindow
from ui.styles import DARK_STYLESHEET

SINGLE_INSTANCE_SERVER_NAME = "ScreenRecorderPro_SingleInstance_drhie"

def setup_windows_app_id():
    """Set explicit AppUserModelID so Windows Taskbar displays custom icon."""
    try:
        myappid = "drhie.screenrecorderpro.bettercam.v1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"[Main] Error setting AppUserModelID: {e}")

def main():
    setup_windows_app_id()

    app = QApplication(sys.argv)
    app.setApplicationName("ScreenRecorder Pro")
    app.setOrganizationName("ProCapture")

    # Single Instance Check
    test_socket = QLocalSocket()
    test_socket.connectToServer(SINGLE_INSTANCE_SERVER_NAME)
    if test_socket.waitForConnected(500):
        # An instance is already running! Signal it to bring its window to front
        test_socket.write(b"ACTIVATE\n")
        test_socket.waitForBytesWritten(1000)
        test_socket.disconnectFromServer()
        print("[Main] Đã có phiên ScreenRecorder Pro đang chạy. Đang kích hoạt cửa sổ hiện tại.")
        sys.exit(0)

    # Allow app to stay alive in system tray when window is closed/hidden
    app.setQuitOnLastWindowClosed(False)

    # Set App Icon
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Apply sleek dark stylesheet
    app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow()

    # Setup local server to handle subsequent launch requests
    local_server = QLocalServer()
    QLocalServer.removeServer(SINGLE_INSTANCE_SERVER_NAME)
    local_server.listen(SINGLE_INSTANCE_SERVER_NAME)

    def on_new_connection():
        client_socket = local_server.nextPendingConnection()
        if client_socket:
            client_socket.waitForReadyRead(500)
            window.showNormal()
            window.activateWindow()
            window.raise_()
            client_socket.disconnectFromServer()

    local_server.newConnection.connect(on_new_connection)

    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
