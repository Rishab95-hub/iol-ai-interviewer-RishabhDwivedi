# Start Admin Portal
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IOL AI Interviewer - Admin Portal" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$venvPath = "C:\Users\risdwivedi\Desktop\Personal\IOL\iol-ai-interviewer-clean\backend\venv"

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "$venvPath\Scripts\Activate.ps1"

Write-Host "Starting Admin Portal..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Admin Portal will be available at: http://localhost:8501" -ForegroundColor Green
Write-Host ""

Set-Location "C:\Users\risdwivedi\Desktop\Personal\IOL\iol-ai-interviewer-clean\frontend"
streamlit run admin_portal.py --server.port=8501
