# Start Frontend Server
# Simple script to start the frontend

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Frontend Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location frontend

Write-Host "Frontend will be available at:" -ForegroundColor Green
Write-Host "  http://localhost:8504" -ForegroundColor White
Write-Host "  http://localhost:8504/voice_interview.html" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python -m http.server 8504
