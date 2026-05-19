@echo off
title On-Call Assistant
cd /d "%~dp0"

echo ============================================
echo   On-Call Assistant - Starting...
echo ============================================
echo.
echo   This may take 30-40 seconds on first run.
echo   Please wait...
echo.

start "On-Call Server" /B python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

echo   Waiting for server to be ready...
:wait
ping -n 3 127.0.0.1 >nul
curl -s http://127.0.0.1:8000/status >nul 2>&1
if errorlevel 1 goto wait

echo   Server is ready!
start http://127.0.0.1:8000

echo.
echo ============================================
echo   http://127.0.0.1:8000
echo   Press Ctrl+C to stop the server
echo ============================================
pause
