@echo off
cd /d "%~dp0"
echo Starting Dashboard...
.\venv\Scripts\python.exe dashboard.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Dashboard failed to start. See error above.
    pause
)
