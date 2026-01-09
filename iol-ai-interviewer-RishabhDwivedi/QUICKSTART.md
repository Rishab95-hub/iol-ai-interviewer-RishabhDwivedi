# Quick Start Guide - IOL AI Interviewer

Get the IOL AI Interviewer running locally in **10 minutes** with this step-by-step guide.

---

## 📋 Prerequisites

Before starting, ensure you have:

- ✅ **Python 3.12** (required for audio features)
- ✅ **PostgreSQL 15+** or **Podman/Docker**
- ✅ **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))
- ✅ **Windows/Linux/macOS** (tested on all platforms)

### Verify Prerequisites

```powershell
# Check Python version
python --version
# Should show: Python 3.12.x

# Check Podman (or Docker)
podman --version
# Should show: podman version 5.x or higher
```

---

## 🚀 Step-by-Step Setup

### Step 1: Clone the Repository (30 seconds)

```powershell
# Navigate to your projects folder
cd C:\Users\YourName\Desktop

# Clone the repository
git clone https://github.com/yourusername/iol-ai-interviewer.git
cd iol-ai-interviewer
```

---

### Step 2: Configure Environment (1 minute)

1. **Create `.env` file in `backend/` folder**:

```powershell
cd backend
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

2. **Edit `backend/.env` and add your OpenAI API key**:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_API_KEY_HERE

# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_interviewer

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
```

**Important**: Replace `YOUR_ACTUAL_API_KEY_HERE` with your real OpenAI API key!

---

### Step 3: Start Database Services (2 minutes)

#### Option A: Using Podman (Recommended)

```powershell
# Start PostgreSQL container
podman run -d `
  --name iol-postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=ai_interviewer `
  -p 5432:5432 `
  postgres:15

# Start Redis container
podman run -d `
  --name iol-redis `
  -p 6379:6379 `
  redis:7-alpine

# Verify containers are running
podman ps
```

#### Option B: Using Docker Compose

```powershell
# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

#### Option C: Local PostgreSQL

If you have PostgreSQL installed locally:

```powershell
# Create database
psql -U postgres -c "CREATE DATABASE ai_interviewer;"
```

---

### Step 4: Setup Python Environment (3 minutes)

```powershell
# Navigate to backend folder
cd backend

# Create virtual environment with Python 3.12
py -3.12 -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# This installs:
# - FastAPI & Uvicorn (Web framework)
# - SQLAlchemy & PostgreSQL driver
# - OpenAI SDK (for GPT-4o-mini)
# - Audio libraries (Whisper, gTTS, edge-tts, pyttsx3)
# - And more...

# Run database migrations
alembic upgrade head

# (Optional) Initialize with sample data
python init_db.py
```

---

### Step 5: Start the Application (1 minute)

#### Automated Start (Easiest)

```powershell
# From project root directory
.\RUN.bat
```

This automatically:
1. ✅ Activates Python virtual environment
2. ✅ Starts FastAPI backend on port 8001
3. ✅ Opens API documentation in browser

#### Manual Start

If you prefer to start services manually:

**Terminal 1 - Backend API**:
```powershell
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**Terminal 2 - Admin Portal**:
```powershell
cd frontend
..\backend\venv\Scripts\activate
streamlit run admin_portal.py --server.port 8501
```

**Terminal 3 - Candidate Portal**:
```powershell
cd frontend
..\backend\venv\Scripts\activate
streamlit run candidate_portal.py --server.port 8502
```

**Terminal 4 - Voice Interview Page**:
```powershell
cd frontend
python -m http.server 8504
```

---

## 🎯 Access the Application

Once all services are running, open your browser:

| Service | URL | Purpose |
|---------|-----|---------|
| **Backend API** | http://localhost:8001 | REST API endpoints |
| **API Docs** | http://localhost:8001/docs | Interactive API documentation |
| **Admin Portal** | http://localhost:8501 | Manage jobs, candidates, interviews |
| **Candidate Portal** | http://localhost:8502 | Apply for jobs, take interviews |
| **Voice Interview** | http://localhost:8504/voice_interview.html | Voice-based interview interface |

---

## 🎤 Conduct Your First Interview

### Method 1: Via Candidate Portal (Recommended)

1. **Open Candidate Portal**: http://localhost:8502

2. **Browse Jobs**:
   - Navigate to "Browse Jobs" tab
   - View available positions

3. **Apply for a Job**:
   - Click "Apply"
   - Enter your details:
     - First Name: John
     - Last Name: Doe
     - Email: john.doe@example.com
   - Upload resume (optional): PDF or TXT file
   - Click "Submit Application"

4. **Start Interview**:
   - Go to "My Applications" tab
   - Find your application
   - Click "Start Interview"
   - Allow microphone access when prompted

5. **Complete Interview**:
   - Answer questions using voice or text
   - System evaluates in real-time
   - Interview ends after 10 questions or manually

6. **View Results**:
   - Open Admin Portal: http://localhost:8501
   - Go to "Interviews" tab
   - Find your interview (status: COMPLETED)
   - Click "📊 Generate Report"
   - View comprehensive assessment

### Method 2: Via Admin Portal

1. **Open Admin Portal**: http://localhost:8501

2. **Create a Job** (if not exists):
   - Navigate to "Jobs" tab
   - Click "Create New Job"
   - Fill in job details:
     - Title: Backend Engineer
     - Department: Engineering
     - Template: backend-engineer
     - Status: Active
   - Click "Create Job"

3. **Add Candidate**:
   - Navigate to "Candidates" tab
   - Click "Add New Candidate"
   - Enter details:
     - First Name: Jane
     - Last Name: Smith
     - Email: jane.smith@example.com
   - Upload resume (optional)
   - Click "Create Candidate"

4. **Schedule Interview**:
   - Navigate to "Interviews" tab
   - Click "Schedule Interview"
   - Select job and candidate
   - Choose template: backend-engineer
   - Click "Schedule"

5. **Start Interview**:
   - Candidate receives interview link
   - Or navigate to Voice Interview page
   - Enter interview ID
   - Complete interview

6. **Generate Report**:
   - Return to Admin Portal → Interviews
   - Find completed interview
   - Click "📊 Generate Report"
   - View all 6 assessment dimensions

---

## ✅ Test the System

### Quick Health Check

```powershell
# Test backend API
Invoke-WebRequest http://localhost:8001/health

# Expected response: {"status": "healthy"}
```

### Test Interview Flow

```powershell
# Create a test interview via API
Invoke-WebRequest -Uri http://localhost:8001/api/jobs -Method POST `
  -ContentType "application/json" `
  -Body '{"title":"Backend Engineer","department":"Engineering","template_type":"backend-engineer","status":"active"}'
```

---

## 🛠️ Troubleshooting

### Issue: Port Already in Use

```powershell
# Kill process on port 8001
$process = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
Stop-Process -Id $process -Force
```

### Issue: Database Connection Failed

```powershell
# Verify PostgreSQL is running
podman ps | Select-String postgres

# If not running, start it
podman start iol-postgres

# Test connection
podman exec -it iol-postgres psql -U postgres -d ai_interviewer -c "SELECT 1;"
```

### Issue: OpenAI API Error

- ✅ Verify API key in `backend/.env`
- ✅ Check key format: starts with `sk-proj-` or `sk-`
- ✅ Ensure no extra spaces or quotes
- ✅ Test key at https://platform.openai.com/api-keys

### Issue: Audio Not Working

1. **Check browser support**: Use Chrome or Edge (best Web Speech API support)
2. **Allow microphone**: Grant browser permission when prompted
3. **Verify audio packages**:
   ```powershell
   cd backend
   .\venv\Scripts\activate
   pip list | Select-String "whisper|gTTS|pyttsx3|edge-tts"
   ```
4. **Reinstall audio dependencies**:
   ```powershell
   pip install openai-whisper gTTS edge-tts pyttsx3 scipy numpy soundfile
   ```

### Issue: Python 3.14 Compatibility

Audio libraries require Python 3.12. If you have 3.14:

```powershell
# Install Python 3.12 from python.org
# Then recreate virtual environment
cd backend
Remove-Item -Recurse -Force venv
py -3.12 -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🔄 Restarting Services

### Quick Restart

```powershell
# Stop backend (Ctrl+C in terminal)
# Restart
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Full Restart (All Services)

```powershell
# Stop all Python processes
Get-Process python* | Stop-Process -Force

# Restart containers
podman restart iol-postgres iol-redis

# Restart application
.\RUN.bat
```

---

## 📚 Next Steps

Once the system is running:

1. ✅ **Explore API Documentation**: http://localhost:8001/docs
2. ✅ **Create Custom Job Templates**: Edit `backend/templates/*.yaml`
3. ✅ **Review Sample Report**: See `docs/SAMPLE_REPORT.md`
4. ✅ **Customize Assessment Rubrics**: Modify dimension weights and scoring
5. ✅ **Deploy to Production**: Follow deployment guide in README.md

---

## 🎥 Demo Video

Watch a complete walkthrough of conducting an interview and generating reports:

[Link to demo video - to be recorded]

---

## 💡 Pro Tips

1. **Use Admin Portal** for initial setup (jobs, candidates)
2. **Use Candidate Portal** for realistic interview simulation
3. **Check Backend Logs** for debugging: Watch terminal where `uvicorn` is running
4. **Database GUI**: Use pgAdmin or DBeaver to inspect database
5. **API Testing**: Use Postman or ThunderClient for advanced API testing

---

## 📞 Need Help?

- **Documentation**: See [README.md](README.md) for detailed information
- **Sample Report**: Check [docs/SAMPLE_REPORT.md](docs/SAMPLE_REPORT.md)
- **Requirements**: Review [REQUIREMENTS_COMPLIANCE.md](REQUIREMENTS_COMPLIANCE.md)
- **GitHub Issues**: Report bugs at repository issues page

---

**You're all set! Start conducting AI-powered interviews! 🚀**
   ```
   http://localhost:8504/voice_interview.html?interview_id=1
   ```

4. Complete the interview (answer 3+ questions)

5. Generate report:
   ```bash
   curl -X POST http://localhost:8001/api/interviews/1/report
   ```

## Troubleshooting

**Backend won't start?**
```bash
# Check PostgreSQL is running
psql -U postgres -c "SELECT 1"

# Verify .env file exists
cat .env
```

**No voice in browser?**
- Use Chrome or Edge (Safari not supported)
- Allow microphone permissions
- Check browser console (F12) for errors

**OpenAI errors?**
```bash
# Test API key
export OPENAI_API_KEY=sk-your-key
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

## Next Steps

- Read full [README.md](README.md) for detailed documentation
- Check [docs/](docs/) folder for guides
- Watch demo video (link in README)
- Explore API at http://localhost:8001/docs

**Need help?** Open an issue on GitHub!
