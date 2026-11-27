# Restart the hidden AI Video Assets service reliably.
# Stop-ScheduledTask alone does NOT kill the detached uvicorn child process,
# so code changes may silently stay inactive. Kill by command line first.
$ErrorActionPreference = 'Stop'
$taskName = 'AI Video Assets Service'

$patterns = @('serve:app', 'service_launcher.py')
$procs = Get-CimInstance Win32_Process | Where-Object {
    $cl = [string]$_.CommandLine
    ($_.Name -like 'python*') -and (($patterns | Where-Object { $cl -like "*$_*" }).Count -gt 0)
}
foreach ($p in $procs) {
    Write-Host ("Stopping PID {0}: {1}" -f $p.ProcessId, $p.CommandLine)
    Stop-Process -Id $p.ProcessId -Force -Confirm:$false -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 4
$state = (Get-ScheduledTask -TaskName $taskName).State
Write-Host ("Task state: {0}" -f $state)
try {
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 10
    Write-Host ("Health: {0}" -f ($health | ConvertTo-Json -Compress))
} catch {
    Write-Warning ("Health check failed: {0}" -f $_.Exception.Message)
}
