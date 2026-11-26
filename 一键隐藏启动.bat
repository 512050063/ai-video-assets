@echo off
title AI Video Assets - Hidden Start
cd /d "%~dp0"
echo Starting AI Video Assets in hidden mode...
start "" /b "C:\Users\abc\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe" "%~dp0service_launcher.py"
echo Waiting for service...
powershell -NoProfile -Command "$ok=$false; for($i=0;$i -lt 30;$i++){ try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 2; if($r.StatusCode -eq 200){ $ok=$true; break } } catch {}; Start-Sleep -Milliseconds 700 }; if($ok){ Write-Host '[OK] Service is running (hidden).'; Write-Host 'LAN URL: http://192.168.100.26:8000' } else { Write-Host '[WARN] Service not responding. Check service.log' }"
timeout /t 3 >nul
