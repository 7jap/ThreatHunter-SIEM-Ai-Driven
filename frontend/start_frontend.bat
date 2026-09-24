@echo off
setlocal
title SIEM Dashboard (Frontend)
echo [INFO] Preparing SIEM Frontend...

cd /d "%~dp0"

if not exist "dist" (
    echo [ERROR] The 'dist' folder is missing! You need to install Node.js and run 'npm run build' first.
    pause
    exit /b 1
)

echo [INFO] Starting Frontend Server (Using Python SPA Server)...
echo ----------------------------------------------------
python serve_frontend.py

echo.
echo [ERROR] Frontend server stopped unexpectedly! Check the errors above.
pause
