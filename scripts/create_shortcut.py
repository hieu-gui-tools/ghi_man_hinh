import os
import sys
import subprocess
from pathlib import Path

# Fix Windows console UTF-8 printing
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def create_desktop_shortcut():
    project_dir = Path(__file__).resolve().parent.parent
    pythonw_path = project_dir / ".venv" / "Scripts" / "pythonw.exe"
    main_path = project_dir / "main.py"
    icon_path = project_dir / "assets" / "icon.ico"
    desktop_dir = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    shortcut_name = "Ghi Man Hinh - ScreenRecorder.lnk"
    shortcut_path = desktop_dir / shortcut_name

    # If pythonw exists, point directly to it; otherwise fallback to run.cmd
    if pythonw_path.exists():
        target = str(pythonw_path)
        args = f'"{str(main_path)}"'
    else:
        target = str(project_dir / "run.cmd")
        args = ""

    ps_script = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{str(shortcut_path)}')
    $Shortcut.TargetPath = '{target}'
    $Shortcut.Arguments = '{args}'
    $Shortcut.WorkingDirectory = '{str(project_dir)}'
    $Shortcut.IconLocation = '{str(icon_path)},0'
    $Shortcut.Description = 'ScreenRecorder Pro - Ghi man hinh & Chup anh sieu toc'
    $Shortcut.Save()
    """

    try:
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"[OK] Da tao shortcut thanh cong tai: {shortcut_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Loi tao shortcut: {e}")
        return False

if __name__ == "__main__":
    create_desktop_shortcut()
