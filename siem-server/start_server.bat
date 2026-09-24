@echo off
setlocal
title SIEM Server (Backend)
echo [INFO] Starting SIEM Server Initialization...

cd /d "%~dp0"

if not exist "app\main.py" (
    echo [ERROR] app\main.py not found in %~dp0. Make sure this script is inside the siem-server folder.
    pause
    exit /b 1
)

echo [INFO] Setting up Python Virtual Environment...
if not exist "venv" (
    python -m venv venv
)

echo [INFO] Installing Python dependencies...
call venv\Scripts\activate.bat
python -m pip install -r requirements.txt --quiet --disable-pip-version-check

echo [INFO] Running Database Migrations...
python -m alembic upgrade head

echo [INFO] Initializing RBAC Default Data...
python app\init_db_data.py

echo [INFO] Launching SIEM Server...
echo ----------------------------------------------------
set PYTHONPATH=%~dp0
python -m app.main

echo.
echo [ERROR] Server stopped unexpectedly! Check the errors above.
pause
