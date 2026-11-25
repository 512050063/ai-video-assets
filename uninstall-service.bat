@echo off
title Uninstall AI Video Assets Auto-Start
cd /d "%~dp0"
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Please right-click this file and "Run as Administrator".
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall-service.ps1"
pause
