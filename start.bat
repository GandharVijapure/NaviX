@echo off
REM ============================================================
REM NaviX - one-command launcher.
REM Backend (FastAPI) serves the frontend too (static HTML/CSS/JS
REM + API + WebSocket, all from one process/port) - so starting
REM this one process is starting "the whole app".
REM
REM First run: creates venv + installs requirements.txt automatically.
REM Every run after that: just starts the server.
REM ============================================================
setlocal
cd /d "%~dp0"

if not exist venv (
    echo [NaviX] No virtual environment found - creating one...
    python -m venv venv
    if errorlevel 1 (
        echo [NaviX] ERROR: could not create venv. Is Python installed and on PATH?
        pause
        exit /b 1
    )
    echo [NaviX] Installing dependencies from requirements.txt...
    venv\Scripts\python.exe -m pip install --upgrade pip
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [NaviX] ERROR: dependency install failed.
        pause
        exit /b 1
    )
)

echo.
echo [NaviX] Starting backend + frontend...
echo [NaviX]   Local:  http://127.0.0.1:8000
echo [NaviX]   LAN:    http://%COMPUTERNAME%:8000  (or this PC's IPv4 from "ipconfig")
echo [NaviX]   Docs:   http://127.0.0.1:8000/docs
echo [NaviX] Press CTRL+C to stop.
echo.

venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

endlocal
