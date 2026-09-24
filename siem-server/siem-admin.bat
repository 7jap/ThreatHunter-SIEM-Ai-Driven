@echo off
setlocal

cd /d "%~dp0"

if not exist "venv" (
    echo [ERROR] Python virtual environment ^(venv^) not found. Please run start_server.bat first.
    exit /b 1
)

call venv\Scripts\activate.bat
python siem_admin.py %*
