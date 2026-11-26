@echo off
title Install AI Video Assets Auto-Start
cd /d "%~dp0"
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Please right-click this file and "Run as Administrator".
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-service.ps1"
echo.
echo [DONE] Service will auto-start on user logon, detached from WorkBuddy.
pause
