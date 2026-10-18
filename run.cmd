@echo off
setlocal
cd /d "%~dp0"
title ScreenRecorder Pro - BetterCam DXGI
echo Starting ScreenRecorder Pro...
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
) else (
    uv run python main.py
)
endlocal
