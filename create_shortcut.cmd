@echo off
setlocal
cd /d "%~dp0"
title Create Desktop Shortcut - ScreenRecorder Pro
echo Creating Desktop Shortcut...
uv run python scripts/create_shortcut.py
echo.
echo Completed! You can launch ScreenRecorder Pro from your Desktop.
pause
endlocal
