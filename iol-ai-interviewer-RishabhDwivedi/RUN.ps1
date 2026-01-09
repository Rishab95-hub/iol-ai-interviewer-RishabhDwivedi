# Complete Setup and Run Script
# Run this from anywhere - it will find the project root automatically

$ErrorActionPreference = "Continue"

# Find project root
$projectRoot = "C:\Users\risdwivedi\Desktop\Personal\IOL\iol-ai-interviewer-clean"
$backendPath = Join-Path $projectRoot "backend"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IOL AI Interviewer - Complete Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check containers
Write-Host "[1/6] Checking database containers..." -ForegroundColor Yellow
$podmanCheck = podman ps 2>&1 | Select-String "iol-postgres"
if (-not $podmanCheck) {
    Write-Host "  Starting containers..." -ForegroundColor Cyan
    podman start iol-postgres iol-redis 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Creating new containers..." -ForegroundColor Cyan
        podman run -d --name iol-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=ai_interviewer -p 5432:5432 postgres:15-alpine 2>&1 | Out-Null
        podman run -d --name iol-redis -p 6379:6379 redis:7-alpine 2>&1 | Out-Null
    }
    Start-Sleep -Seconds 3
}
Write-Host "  Containers running!" -ForegroundColor Green
Write-Host ""

# Navigate to backend
Set-Location $backendPath

# Create venv with Python 3.12
Write-Host "[2/6] Setting up virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    # Try to use Python 3.12, fall back to default python
    $py312 = & py -3.12 -c "print('ok')" 2>&1
    if ($py312 -eq "ok") {
        py -3.12 -m venv venv
    } else {
        python -m venv venv
    }
}
Write-Host "  Done!" -ForegroundColor Green
Write-Host ""

# Install packages
Write-Host "[3/6] Installing Python packages..." -ForegroundColor Yellow
$pipExe = Join-Path $backendPath "venv\Scripts\pip.exe"
$pythonExe = Join-Path $backendPath "venv\Scripts\python.exe"

& $pipExe install --upgrade pip 2>&1 | Out-Null

# Install all packages including audio support (works with Python 3.12)
$allPackages = "fastapi uvicorn[standard] sqlalchemy alembic asyncpg redis openai pydantic pydantic-settings python-dotenv httpx aiofiles websockets python-multipart pyyaml PyPDF2 python-docx tenacity structlog python-dateutil email-validator hiredis streamlit pandas soundfile pydub scipy numpy openai-whisper ffmpeg-python gTTS edge-tts pyttsx3"

Write-Host "  Installing dependencies..." -ForegroundColor Cyan
& $pipExe install $allPackages.Split(" ") 2>&1 | Out-Null
Write-Host "  Done!" -ForegroundColor Green
Write-Host ""

# Initialize database
Write-Host "[4/6] Initializing database..." -ForegroundColor Yellow
& $pythonExe init_db.py 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Done!" -ForegroundColor Green
} else {
    Write-Host "  Warning: Check if containers are ready" -ForegroundColor Yellow
}
Write-Host ""

# Create storage directories
Write-Host "[5/6] Creating storage directories..." -ForegroundColor Yellow
$dirs = @("storage", "storage\reports", "storage\transcripts", "storage\audio", "uploads", "uploads\resumes")
foreach ($dir in $dirs) {
    $fullPath = Join-Path $backendPath "..\$dir"
    New-Item -ItemType Directory -Path $fullPath -Force 2>&1 | Out-Null
}
Write-Host "  Done!" -ForegroundColor Green
Write-Host ""

# Start server
Write-Host "[6/6] Starting backend server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Backend API is starting!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "URLs:" -ForegroundColor Cyan
Write-Host "  http://localhost:8001" -ForegroundColor White
Write-Host "  http://localhost:8001/docs (API Documentation)" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

& $pythonExe -m uvicorn app.main:app --host 0.0.0.0 --port 8001
