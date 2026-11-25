# Remove the AI Video Assets scheduled task and firewall rule.
$ErrorActionPreference = 'Stop'
$taskName = 'AI Video Assets Service'
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "[OK] Scheduled task removed: $taskName"
netsh advfirewall firewall delete rule name="AI Video Assets 8000" | Out-Null
Write-Host '[OK] Firewall rule removed'
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Host ("[OK] Stopped listener PID " + $_.OwningProcess)
}
