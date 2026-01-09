# Start Candidate Portal
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IOL AI Interviewer - Candidate Portal" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$venvPath = "C:\Users\risdwivedi\Desktop\Personal\IOL\iol-ai-interviewer-RishabhDwivedi\backend\venv"

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "$venvPath\Scripts\Activate.ps1"

Write-Host "Starting Candidate Portal..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Candidate Portal will be available at: http://localhost:8502" -ForegroundColor Green
Write-Host ""

Set-Location "C:\Users\risdwivedi\Desktop\Personal\IOL\iol-ai-interviewer-RishabhDwivedi\frontend"
streamlit run candidate_portal.py --server.port=8502
