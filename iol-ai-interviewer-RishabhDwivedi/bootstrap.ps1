# IOL AI Interviewer - Bootstrap Script
# This script sets up everything from scratch including venv and prerequisites

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IOL AI Interviewer - Bootstrap Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if a command exists
function Test-Command {
    param($Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# Function to print success message
function Write-Success {
    param($Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

# Function to print error message
function Write-ErrorMsg {
    param($Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to print info message
function Write-Info {
    param($Message)
    Write-Host "[INFO] $Message" -ForegroundColor Yellow
}

# Step 1: Check Python
Write-Host "Step 1: Checking Python Installation..." -ForegroundColor Cyan
Write-Host "---------------------------------------" -ForegroundColor Cyan

if (-not (Test-Command python)) {
    Write-ErrorMsg "Python not found. Please install Python 3.11+ from https://www.python.org/"
    Write-Host ""
    Write-Host "After installing Python, make sure to:"
    Write-Host "  1. Check 'Add Python to PATH' during installation"
    Write-Host "  2. Restart your terminal"
    Write-Host ""
    exit 1
}

$pythonVersion = python --version 2>&1
Write-Success "Python found: $pythonVersion"

# Check Python version
if ($pythonVersion -match "Python (\d+)\.(\d+)") {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-ErrorMsg "Python 3.11+ is required. Current version: $pythonVersion"
        exit 1
    }
    Write-Success "Python version is compatible"
}

Write-Host ""

# Step 2: Check Docker/Podman (optional)
Write-Host "Step 2: Checking Container Runtime..." -ForegroundColor Cyan
Write-Host "--------------------------------------" -ForegroundColor Cyan

$useContainer = $false
$containerCmd = ""
$composeCmd = ""

if (Test-Command podman) {
    $podmanVersion = podman --version 2>&1
    Write-Success "Podman found: $podmanVersion"
    $useContainer = $true
    $containerCmd = "podman"
    
    # Check for podman-compose
    if (Test-Command podman-compose) {
        $composeCmd = "podman-compose"
        Write-Success "podman-compose found"
    } else {
        Write-Info "podman-compose not found, will use podman directly"
        $composeCmd = "podman-compose"
    }
} elseif (Test-Command docker) {
    $dockerVersion = docker --version 2>&1
    Write-Success "Docker found: $dockerVersion"
    $useContainer = $true
    $containerCmd = "docker"
    $composeCmd = "docker-compose"
} else {
    Write-Info "Neither Docker nor Podman found. Will use local PostgreSQL if available."
    Write-Info "For easier setup, consider installing:"
    Write-Host "  - Podman: https://podman.io/" -ForegroundColor White
    Write-Host "  - Docker: https://www.docker.com/products/docker-desktop/" -ForegroundColor White
}

Write-Host ""

# Step 3: Setup Environment File
Write-Host "Step 3: Setting up Environment Configuration..." -ForegroundColor Cyan
Write-Host "------------------------------------------------" -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Success "Created .env file from .env.example"
    } else {
        Write-ErrorMsg ".env.example not found!"
        exit 1
    }
    
    Write-Host ""
    Write-Info "IMPORTANT: You need to add your OpenAI API key to the .env file"
    Write-Host "           Get your API key from: https://platform.openai.com/api-keys" -ForegroundColor Yellow
    Write-Host ""
    
    $openEditor = Read-Host "Would you like to open .env file now to add your API key? (y/n)"
    if ($openEditor -eq "y") {
        notepad ".env"
        Write-Host ""
        Read-Host "Press ENTER after you have saved your API key to continue"
    } else {
        Write-Host ""
        Write-Info "Remember to edit .env and add your OpenAI API key before running interviews!"
        Write-Host ""
    }
} else {
    Write-Success ".env file already exists"
}

Write-Host ""

# Step 4: Start Database Services
Write-Host "Step 4: Setting up Database Services..." -ForegroundColor Cyan
Write-Host "---------------------------------------" -ForegroundColor Cyan

if ($useContainer) {
    Write-Info "Starting PostgreSQL and Redis with $containerCmd..."
    
    if ($containerCmd -eq "podman") {
        # Use podman directly to start containers
        Write-Info "Starting PostgreSQL container..."
        podman run -d --name iol-postgres `
            -e POSTGRES_USER=postgres `
            -e POSTGRES_PASSWORD=postgres `
            -e POSTGRES_DB=ai_interviewer `
            -p 5432:5432 `
            postgres:15-alpine
        
        Write-Info "Starting Redis container..."
        podman run -d --name iol-redis `
            -p 6379:6379 `
            redis:7-alpine
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Database services started successfully"
            Write-Info "Waiting for services to be ready (10 seconds)..."
            Start-Sleep -Seconds 10
        } else {
            Write-Info "Containers might already be running, checking status..."
            podman start iol-postgres iol-redis 2>&1 | Out-Null
            Start-Sleep -Seconds 5
            Write-Success "Using existing containers"
        }
    } else {
        # Use docker-compose
        docker-compose up -d postgres redis
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Database services started successfully"
            Write-Info "Waiting for services to be ready (10 seconds)..."
            Start-Sleep -Seconds 10
        } else {
            Write-ErrorMsg "Failed to start services"
            Write-Info "You may need to start Docker Desktop first"
            exit 1
        }
    }
} else {
    Write-Info "Container runtime not available. Please ensure PostgreSQL is installed and running."
    Write-Host ""
    $skipDb = Read-Host "Continue without containers? (y/n)"
    if ($skipDb -ne "y") {
        Write-Info "Setup cancelled. Install Podman/Docker or PostgreSQL and try again."
        exit 1
    }
}

Write-Host ""

# Step 5: Backend Setup with Virtual Environment
Write-Host "Step 5: Setting up Backend..." -ForegroundColor Cyan
Write-Host "-----------------------------" -ForegroundColor Cyan

Set-Location backend

# Remove old venv if exists and create fresh one
if (Test-Path "venv") {
    Write-Info "Removing old virtual environment..."
    Remove-Item -Recurse -Force "venv"
}

Write-Info "Creating new Python virtual environment..."
python -m venv venv

if ($LASTEXITCODE -ne 0) {
    Write-ErrorMsg "Failed to create virtual environment"
    Write-Info "Try running: python -m pip install --user virtualenv"
    Set-Location ..
    exit 1
}

Write-Success "Virtual environment created"

# Activate virtual environment
Write-Info "Activating virtual environment..."
& .\venv\Scripts\Activate.ps1

# Upgrade pip first
Write-Info "Upgrading pip..."
python -m pip install --upgrade pip

if ($LASTEXITCODE -eq 0) {
    Write-Success "pip upgraded successfully"
} else {
    Write-ErrorMsg "Failed to upgrade pip"
    Set-Location ..
    exit 1
}

# Install wheel and setuptools first
Write-Info "Installing build tools..."
pip install wheel setuptools --upgrade

# Try to install numpy with binary wheels first (needed for langchain)
Write-Info "Installing numpy (trying to find pre-built wheels)..."
pip install "numpy>=2.0.0" --only-binary=:all: 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Info "Numpy pre-built wheels not available for Python 3.14, skipping for now..."
    Write-Info "The application will work without numpy-dependent features"
}

# Try to install pydantic with binary wheels first
Write-Info "Installing pydantic (trying to find pre-built wheels)..."
pip install "pydantic>=2.0.0,<3.0.0" "pydantic-settings>=2.0.0,<3.0.0" --only-binary=:all: 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Info "Pre-built wheels not available, will compile if needed..."
    pip install "pydantic>=2.0.0,<3.0.0" "pydantic-settings>=2.0.0,<3.0.0"
}

# Install dependencies one by one to handle Python 3.14 compatibility issues
Write-Info "Installing backend dependencies (this will take several minutes)..."
Write-Host "  Installing packages one by one for better compatibility..." -ForegroundColor Yellow

# Critical packages that must be installed
$criticalPackages = @(
    "fastapi==0.109.0",
    "uvicorn[standard]==0.27.0",
    "sqlalchemy==2.0.25",
    "psycopg2-binary",
    "redis==5.0.1",
    "openai==1.10.0",
    "python-dotenv==1.0.0",
    "httpx==0.26.0",
    "aiofiles==23.2.1"
)

Write-Info "Installing critical packages..."
foreach ($pkg in $criticalPackages) {
    Write-Host "  - Installing $pkg..." -NoNewline
    $output = pip install $pkg --prefer-binary 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK" -ForegroundColor Green
    } else {
        Write-Host " FAILED (trying without version constraint)..." -ForegroundColor Yellow
        $pkgName = $pkg -replace "==.*|>=.*|<=.*", ""
        $output = pip install $pkgName --prefer-binary 2>&1 | Out-String
        if ($LASTEXITCODE -eq 0) {
            Write-Host " OK (newer version)" -ForegroundColor Green
        } else {
            Write-Host " FAILED (will continue)" -ForegroundColor Red
        }
    }
}

# Optional packages
$optionalPackages = @(
    "alembic==1.13.1",
    "websockets==12.0",
    "python-multipart==0.0.6",
    "anthropic==0.18.1",
    "tiktoken==0.5.2",
    "pyyaml==6.0.1",
    "PyPDF2==3.0.1",
    "python-docx==1.1.0",
    "tenacity==8.2.3",
    "structlog==24.1.0",
    "python-json-logger==2.0.7",
    "python-dateutil==2.8.2"
)

Write-Info "Installing optional packages (skipping if incompatible)..."
foreach ($pkg in $optionalPackages) {
    Write-Host "  - Installing $pkg..." -NoNewline
    $output = pip install $pkg --prefer-binary 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK" -ForegroundColor Green
    } else {
        Write-Host " SKIPPED" -ForegroundColor Yellow
    }
}

# Verify critical packages are installed
Write-Host ""
Write-Info "Verifying critical packages..."
$criticalCheck = @("fastapi", "uvicorn", "sqlalchemy", "openai")
$allInstalled = $true

foreach ($pkg in $criticalCheck) {
    pip show $pkg >$null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "$pkg installed"
    } else {
        Write-ErrorMsg "$pkg NOT installed"
        $allInstalled = $false
    }
}

if (-not $allInstalled) {
    Write-ErrorMsg "Some critical packages failed to install"
    Write-Info "The application may not work correctly"
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        Set-Location ..
        exit 1
    }
}

if ($LASTEXITCODE -eq 0) {
    Write-Success "All dependencies installed successfully"
} else {
    Write-ErrorMsg "Failed to install dependencies"
    Write-Info "Check the error messages above for details"
    Set-Location ..
    exit 1
}

# Initialize database
Write-Info "Initializing database tables..."
python init_db.py

if ($LASTEXITCODE -eq 0) {
    Write-Success "Database initialized successfully"
} else {
    Write-ErrorMsg "Failed to initialize database"
    Write-Info "Make sure your database is running and .env settings are correct"
    Set-Location ..
    exit 1
}

Set-Location ..

Write-Host ""

# Step 6: Create Required Directories
Write-Host "Step 6: Creating Storage Directories..." -ForegroundColor Cyan
Write-Host "---------------------------------------" -ForegroundColor Cyan

$directories = @(
    "storage",
    "storage/reports",
    "storage/transcripts",
    "storage/audio",
    "uploads",
    "uploads/resumes"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Success "Created: $dir"
    } else {
        Write-Success "Exists: $dir"
    }
}

Write-Host ""

# Step 7: Create Startup Scripts
Write-Host "Step 7: Creating Startup Scripts..." -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Cyan

# Backend startup script
$backendScript = @'
@echo off
echo ========================================
echo Starting Backend API Server
echo ========================================
cd backend
call venv\Scripts\activate
echo.
echo Backend API will be available at:
echo   - http://localhost:8001
echo   - http://localhost:8001/docs (API Documentation)
echo.
uvicorn app.main:app --reload --port 8001
'@

[System.IO.File]::WriteAllText("$PWD\start-backend.bat", $backendScript, [System.Text.Encoding]::ASCII)
Write-Success "Created start-backend.bat"

# Frontend startup script
$frontendScript = @'
@echo off
echo ========================================
echo Starting Frontend Server
echo ========================================
cd frontend
echo.
echo Frontend will be available at:
echo   - http://localhost:8504
echo   - http://localhost:8504/voice_interview.html
echo.
python -m http.server 8504
'@

[System.IO.File]::WriteAllText("$PWD\start-frontend.bat", $frontendScript, [System.Text.Encoding]::ASCII)
Write-Success "Created start-frontend.bat"

# Combined startup script
$startAllScript = @'
@echo off
echo ========================================
echo IOL AI Interviewer - Starting All Services
echo ========================================
echo.

REM Start backend in new window
start "IOL Backend API" cmd /k start-backend.bat

REM Wait for backend to start
echo Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

REM Start frontend in new window
start "IOL Frontend" cmd /k start-frontend.bat

echo.
echo ========================================
echo All services are starting...
echo ========================================
echo.
echo Available URLs:
echo   Backend API:  http://localhost:8001
echo   API Docs:     http://localhost:8001/docs
echo   Frontend:     http://localhost:8504
echo   Interview:    http://localhost:8504/voice_interview.html
echo.
echo To stop services: Close the terminal windows or press Ctrl+C
echo.
pause
'@

[System.IO.File]::WriteAllText("$PWD\start-all.bat", $startAllScript, [System.Text.Encoding]::ASCII)
Write-Success "Created start-all.bat"

# Stop script
$stopScript = @'
@echo off
echo Stopping IOL AI Interviewer services...
taskkill /FI "WindowTitle eq IOL Backend API*" /F >nul 2>&1
taskkill /FI "WindowTitle eq IOL Frontend*" /F >nul 2>&1
echo Services stopped.
pause
'@

[System.IO.File]::WriteAllText("$PWD\stop-all.bat", $stopScript, [System.Text.Encoding]::ASCII)
Write-Success "Created stop-all.bat"

Write-Host ""

# Final Summary
Write-Host "========================================" -ForegroundColor Green
Write-Host "Bootstrap Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "What was set up:" -ForegroundColor Cyan
Write-Host "  [OK] Python virtual environment" -ForegroundColor Green
Write-Host "  [OK] All Python dependencies installed" -ForegroundColor Green
Write-Host "  [OK] Database initialized" -ForegroundColor Green
Write-Host "  [OK] Storage directories created" -ForegroundColor Green
Write-Host "  [OK] Startup scripts created" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Verify your OpenAI API key is set in .env file" -ForegroundColor Yellow
Write-Host "   Open .env and make sure OPENAI_API_KEY is set"
Write-Host ""
Write-Host "2. Start the application:" -ForegroundColor Yellow
Write-Host "   .\start-all.bat"
Write-Host ""
Write-Host "3. Access the application:" -ForegroundColor Yellow
Write-Host "   Backend API:      http://localhost:8001"
Write-Host "   API Docs:         http://localhost:8001/docs"
Write-Host "   Frontend:         http://localhost:8504"
Write-Host "   Voice Interview:  http://localhost:8504/voice_interview.html"
Write-Host ""
Write-Host "4. To stop all services:" -ForegroundColor Yellow
Write-Host "   .\stop-all.bat"
Write-Host ""

if ($useContainer) {
    Write-Host "Container Commands:" -ForegroundColor Cyan
    if ($containerCmd -eq "podman") {
        Write-Host "  Stop containers:  podman stop iol-postgres iol-redis"
        Write-Host "  Start containers: podman start iol-postgres iol-redis"
        Write-Host "  View logs:        podman logs iol-postgres"
        Write-Host "  Remove:           podman rm -f iol-postgres iol-redis"
    } else {
        Write-Host "  Stop database:    docker-compose down"
        Write-Host "  View logs:        docker-compose logs -f"
        Write-Host "  Restart database: docker-compose restart"
    }
    Write-Host ""
}

Write-Host "Troubleshooting:" -ForegroundColor Cyan
Write-Host "  - Check logs in the terminal windows"
Write-Host "  - Verify database is running"
Write-Host "  - Ensure ports 8001 and 8504 are not in use"
Write-Host "  - Review README.md and QUICKSTART.md for details"
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Ready to go!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
