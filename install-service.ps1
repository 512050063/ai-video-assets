# Install AI Video Assets as a Windows Scheduled Task (auto-start at user logon).
# Run as Administrator. Uses pythonw.exe + service_launcher.py so no console
# window appears and the service runs detached from the launching shell.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcher = Join-Path $root 'service_launcher.py'

if (-not (Test-Path $launcher)) { throw "Missing launcher: $launcher" }

$taskName = 'AI Video Assets Service'

# 1) Resolve a usable Python (pythonw.exe preferred for no console)
$pyw = ''
$candidates = @()
$cfg = Join-Path $root 'service-config.bat'
if (Test-Path $cfg) {
    $m = Select-String -Path $cfg -Pattern 'set "PY=(.*)"' | Select-Object -First 1
    if ($m) { $candidates += $m.Matches[0].Groups[1].Value }
}
$versionsDir = Join-Path $env:USERPROFILE '.workbuddy\binaries\python\versions'
if (Test-Path $versionsDir) {
    Get-ChildItem $versionsDir -Directory | Sort-Object Name -Descending | ForEach-Object {
        $candidates += (Join-Path $_.FullName 'python.exe')
    }
}
foreach ($c in $candidates) {
    if (-not $c -or -not (Test-Path $c)) { continue }
    $candidatePyw = Join-Path (Split-Path -Parent $c) 'pythonw.exe'
    if (-not (Test-Path $candidatePyw)) { continue }
    $ver = & $c -c "import sys; sys.stdout.write('{}.{}'.format(*sys.version_info[:2]))" 2>$null
    if ($LASTEXITCODE -eq 0 -and $ver -eq '3.13') { $pyw = $candidatePyw; break }
}
if (-not $pyw) {
    # Fallback: try `python` on PATH
    try {
        $resolved = (Get-Command python -ErrorAction Stop).Source
        $candidatePyw = Join-Path (Split-Path -Parent $resolved) 'pythonw.exe'
        if (Test-Path $candidatePyw) { $pyw = $candidatePyw }
    } catch { }
}
if (-not $pyw) { throw 'No usable pythonw.exe (Python 3.13) found.' }
Write-Host "[OK] Launcher interpreter: $pyw"

# 2) Persist Python path for the launcher script
$pyexe = Join-Path (Split-Path -Parent $pyw) 'python.exe'
Set-Content -Path $cfg -Value "set `"PY=$pyexe`"" -Encoding ASCII

# 3) Firewall rule for TCP 8000
netsh advfirewall firewall delete rule name="AI Video Assets 8000" | Out-Null
netsh advfirewall firewall add rule name="AI Video Assets 8000" dir=in action=allow protocol=TCP localport=8000 | Out-Null
Write-Host '[OK] Firewall rule: TCP 8000'

# 4) Register scheduled task: AtLogOn, hidden (pythonw), highest privileges
$action = New-ScheduledTaskAction -Execute $pyw -Argument ('"{0}"' -f $launcher)
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'AI Video Assets hidden LAN service, detached from WorkBuddy' | Out-Null
Write-Host "[OK] Scheduled task registered: $taskName"

# 5) Remove legacy Startup-folder entry and stale VBS launcher
$legacy = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\AI-Video-Assets-Service.vbs'
if (Test-Path $legacy) { Remove-Item $legacy -Force; Write-Host '[OK] Removed legacy Startup-folder entry' }
