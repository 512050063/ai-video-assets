@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

title AI Video Assets Launcher
echo ==========================================================
echo   AI Video Assets - auto start
echo   backend : http://127.0.0.1:8000
echo   frontend: http://localhost:5173
echo ==========================================================
echo.

rem ---------- 1. environment check ----------
rem Find a REAL python: the WindowsApps\python.exe is only a
rem Microsoft Store stub which runs no code and has no pip.
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
    echo [ERROR] No usable Python found. Install Python 3.9+ first.
    pause
    exit /b 1
)
echo [OK] Python: %PY%

node -v >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found in PATH. Install Node 18+ first.
    pause
    exit /b 1
)
echo [OK] Node.js detected.

rem ---------- 2. kill old processes on 8000 / 5173 ----------
call :killport 8000
call :killport 5173

rem ---------- 3. dependencies ----------
"%PY%" -c "import fastapi, uvicorn, sqlalchemy, jwt" >nul 2>nul
if errorlevel 1 (
    echo [SETUP] Installing backend dependencies...
    "%PY%" -m pip install -r backend\requirements.txt -q
    if errorlevel 1 (
        echo [ERROR] Backend dependency install failed. Details below:
        echo ------------------------------------------------------------
        "%PY%" -m pip install -r backend\requirements.txt
        echo ------------------------------------------------------------
        pause
        exit /b 1
    )
)
echo [OK] Backend dependencies ready.

if not exist "frontend\node_modules" (
    echo [SETUP] Installing frontend dependencies, this may take a while...
    pushd frontend
    call npm install
    popd
)
echo [OK] Frontend dependencies ready.

rem ---------- 4. start backend ----------
echo [START] Backend ...
start "ai-video-backend" /D "%~dp0backend" cmd /k ""%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

rem ---------- 5. start frontend ----------
echo [START] Frontend ...
start "ai-video-frontend" /D "%~dp0frontend" cmd /k npm run dev

rem ---------- 6. wait until both are reachable ----------
echo [WAIT] Waiting for backend http://127.0.0.1:8000 ...
call :waiturl "http://127.0.0.1:8000/api/health" 60
if errorlevel 1 (
    echo [ERROR] Backend did not respond in time. Check the backend window.
    pause
    exit /b 1
)
echo [OK] Backend is up.

echo [WAIT] Waiting for frontend http://localhost:5173 ...
call :waiturl "http://localhost:5173" 60
if errorlevel 1 (
    echo [ERROR] Frontend did not respond in time. Check the frontend window.
    pause
    exit /b 1
)
echo [OK] Frontend is up.

rem ---------- 7. open browser ----------
start "" "http://localhost:5173"
echo.
echo [DONE] Browser opened. Close the two service windows to stop the app.
echo.
ping -n 4 127.0.0.1 >nul
exit /b 0


:findpy
rem Verify candidate actually executes code and is Python 3.9+
set "CAND=%~1"
if not defined CAND exit /b 1
"%CAND%" -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,9) else 1)" >nul 2>nul
if errorlevel 1 exit /b 1
"%CAND%" -c "print('PYOK')" > "%TEMP%\avm_pycheck.txt" 2>nul
if errorlevel 1 exit /b 1
findstr /x "PYOK" "%TEMP%\avm_pycheck.txt" >nul 2>nul
if errorlevel 1 exit /b 1
set "PY=%CAND%"
exit /b 0


:killport
set "PORT=%~1"
set "FOUND="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr LISTENING ^| findstr /c:":%PORT%"') do (
    if not "%%p"=="0" (
        echo [KILL] Port %PORT% is busy, terminating PID %%p ...
        taskkill /f /pid %%p >nul 2>nul
        set "FOUND=1"
    )
)
if not defined FOUND echo [OK] Port %PORT% is free.
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
