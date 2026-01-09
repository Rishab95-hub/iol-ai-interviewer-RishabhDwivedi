# Manual Setup Guide for Python 3.14

## Quick Setup (If bootstrap.ps1 is having issues)

### 1. Start Database Containers
```powershell
# Start Podman containers
podman start iol-postgres iol-redis

# Or create them if they don't exist:
podman run -d --name iol-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=ai_interviewer -p 5432:5432 postgres:15-alpine
podman run -d --name iol-redis -p 6379:6379 redis:7-alpine
```

### 2. Setup Backend
```powershell
cd backend

# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install ONLY critical packages (skip packages that fail)
pip install fastapi uvicorn[standard] sqlalchemy psycopg2-binary redis openai python-dotenv httpx aiofiles

# Install optional packages one by one
pip install alembic websockets python-multipart pyyaml PyPDF2 python-docx tenacity structlog python-dateutil

# Initialize database
python init_db.py

cd ..
```

### 3. Start the Application
```powershell
# Start backend (in one terminal)
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8001

# Start frontend (in another terminal)
cd frontend
python -m http.server 8504
```

### 4. Access the Application
- Backend API: http://localhost:8001
- API Docs: http://localhost:8001/docs
- Frontend: http://localhost:8504
- Voice Interview: http://localhost:8504/voice_interview.html

## Notes for Python 3.14

Python 3.14 is very new (released in 2026). Some packages may not install:
- **tiktoken** - May fail (optional, for token counting)
- **anthropic** - May need newer version
- **langchain** - Requires numpy which may not have wheels

The core functionality (FastAPI, OpenAI, Database) will work fine without these packages.

## Troubleshooting

### If database connection fails:
Check if containers are running:
```powershell
podman ps
```

Restart containers:
```powershell
podman restart iol-postgres iol-redis
```

### If packages fail to install:
Skip them and continue - the app will work with just the critical packages listed above.
