@echo off
rem Internal launcher used by the boot-time scheduled task.
setlocal
cd /d "%~dp0"
if exist "%~dp0service-config.bat" call "%~dp0service-config.bat"

if not defined PY (
    call :findpy python
    if not defined PY (
        for /f "delims=" %%v in ('dir /b /ad /o-n "%USERPROFILE%\.workbuddy\binaries\python\versions" 2^>nul') do (
            if not defined PY call :findpy "%USERPROFILE%\.workbuddy\binaries\python\versions\%%v\python.exe"
        )
    )
)
if not defined PY (
    echo [%date% %time%] ERROR: no usable Python found >> "%~dp0service.log"
    exit /b 1
)

echo [%date% %time%] Service starting >> "%~dp0service.log"
cd /d "%~dp0backend"
"%PY%" -m uvicorn serve:app --host 0.0.0.0 --port 8000 >> "%~dp0service.log" 2>&1
echo [%date% %time%] Service stopped >> "%~dp0service.log"
exit /b 0

:findpy
set "CAND=%~1"
if not defined CAND exit /b 1
"%CAND%" -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,9) else 1)" >nul 2>nul
if errorlevel 1 exit /b 1
set "PY=%CAND%"
exit /b 0
