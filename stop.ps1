Write-Host "Stopping AMLO stack..." -ForegroundColor Cyan

Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "  Python services stopped." -ForegroundColor Yellow

Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "  Node/Next.js stopped." -ForegroundColor Yellow

Get-Process powershell | Where-Object { $_.Id -ne $PID } | Stop-Process -Force
Write-Host "  Terminals closed." -ForegroundColor Yellow

Write-Host "Done." -ForegroundColor Green
