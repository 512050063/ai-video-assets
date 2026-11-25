@echo off
setlocal enabledelayedexpansion
title AI Video Assets - LAN One-Click Start
cd /d "%~dp0"

echo ============================================================
echo   AI Video Assets - LAN Deployment (single port 8000)
echo ============================================================
echo.

rem ---------- 1. locate a real Python (skip Store stub) ----------
set "PY="
call :findpy python
if not defined PY (
    for /f "delims=" %%v in ('dir /b /ad /o-n "%USERPROFILE%\.workbuddy\binaries\python\versions" 2^>nul') do (
        if not defined PY call :findpy "%USERPROFILE%\.workbuddy\binaries\python\versions\%%v\python.exe"
    )
)
if not defined PY (
    for /f "delims=" %%v in ('dir /b /ad /o-n "%LOCALAPPDATA%\Programs\Python" 2^>nul') do (
        if not defined PY call :findpy "%LOCALAPPDATA%\Programs\Python\%%v\python.exe"
    )
)
if not defined PY (
    for /f "delims=" %%v in ('dir /b /ad /o-n "C:\Python3*" 2^>nul') do (
        if not defined PY call :findpy "C:\%%v\python.exe"
    )
)
if not defined PY (
    echo [ERROR] No usable Python 3.9+ found. Install Python first.
    pause
    exit /b 1
)
echo [OK] Python: %PY%

rem ---------- 2. dependency check / install ----------
"%PY%" -c "import fastapi, uvicorn, sqlalchemy, jwt, multipart" >nul 2>nul
if errorlevel 1 (
    echo [SETUP] Installing backend dependencies ...
    if defined HTTPS_PROXY (
        "%PY%" -m pip install -r backend\requirements.txt --proxy %HTTPS_PROXY% -q
    ) else (
        "%PY%" -m pip install -r backend\requirements.txt -q
    )
    if errorlevel 1 (
        echo [ERROR] Dependency install failed.
        pause
        exit /b 1
    )
)
echo [OK] Dependencies ready.

rem ---------- 3. free port 8000 ----------
call :killport 8000

rem ---------- 4. detect LAN IP ----------
set "LANIP="
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "CAND=%%a"
    set "CAND=!CAND: =!"
    if not "!CAND!"=="127.0.0.1" if not defined LANIP set "LANIP=!CAND!"
)
if not defined LANIP set "LANIP=127.0.0.1"

echo.
echo   Local : http://localhost:8000
echo   LAN   : http://!LANIP!:8000
echo   Health: http://!LANIP!:8000/api/health
echo.
echo   Default login: admin / admin123456  (change after first login)
echo.

rem ---------- 5. start service ----------
echo [START] Launching service ...
start "AI Video Assets Service" /D "%~dp0backend" cmd /k ""%PY%" -m uvicorn serve:app --host 0.0.0.0 --port 8000"

echo [WAIT] Waiting for service ...
call :waiturl "http://127.0.0.1:8000/api/health" 60
if errorlevel 1 (
    echo [ERROR] Service did not respond. Check the service window.
    pause
    exit /b 1
)
echo [OK] Service is up.
start "" "http://localhost:8000"
echo.
echo [DONE] Browser opened. Close the "AI Video Assets Service" window to stop.
echo.
ping -n 4 127.0.0.1 >nul
exit /b 0


:findpy
set "CAND=%~1"
if not defined CAND exit /b 1
"%CAND%" -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,9) else 1)" >nul 2>nul
if errorlevel 1 exit /b 1
set "PY=%CAND%"
exit /b 0


:killport
set "PORT=%~1"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr LISTENING ^| findstr /c:":%PORT%"') do (
    if not "%%p"=="0" taskkill /f /pid %%p >nul 2>nul
)
exit /b 0


:waiturl
set "URL=%~1"
set /a WAITN=0
:waitloop
set /a WAITN+=1
curl -s -o nul --max-time 2 "%URL%" >nul 2>nul
if not errorlevel 1 exit /b 0
if %WAITN% GEQ %~2 exit /b 1
ping -n 2 127.0.0.1 >nul
goto waitloop
