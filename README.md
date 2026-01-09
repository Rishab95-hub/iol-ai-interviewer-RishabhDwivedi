# IOL AI Interviewer - Voice-Based Interview Platform

## 📋 Project Description

An intelligent voice-based interview platform that conducts automated technical interviews using AI. The system evaluates candidates across multiple dimensions in real-time, generates comprehensive assessment reports, and provides hiring recommendations.

### Key Features

- **Voice-Based Interviews**: Real-time voice interaction using Web Speech API
- **Multi-Dimensional Assessment**: Evaluates candidates on 6 key dimensions:
  - Technical Knowledge (25%)
  - Problem-Solving Approach (25%)
  - Code Quality & Best Practices (20%)
  - System Design & Architecture (10%)
  - Communication Clarity (10%)
  - Cultural Fit (10%)
- **Real-Time Scoring**: Continuous evaluation during the interview
- **Comprehensive Reports**: Detailed assessment with strengths, concerns, evidence, and recommendations
- **Four-Tier Recommendations**: Strong Hire / Hire / No Hire / Strong No Hire
- **Template-Based**: Customizable assessment templates (includes Backend Engineer template)

### Objectives

1. Automate technical screening interviews
2. Provide consistent, bias-free candidate evaluation
3. Generate actionable insights for hiring decisions
4. Reduce time-to-hire through parallel interview processing

---

## 🏗️ Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                             │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Voice Interview  │  │  Admin Portal    │                │
│  │   (HTML/JS)      │  │   (Streamlit)    │                │
│  └────────┬─────────┘  └────────┬─────────┘                │
└───────────┼──────────────────────┼──────────────────────────┘
            │                      │
            │    HTTP/WebSocket    │
            ▼                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend API (FastAPI)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Interview Manager  │  Assessment Service             │  │
│  │  ┌──────────────┐   │  ┌────────────────────┐       │  │
│  │  │ Job          │   │  │ Real-time Scoring  │       │  │
│  │  │ Candidate    │   │  │ Evidence Collection│       │  │
│  │  │ Interview    │   │  │ Report Generation  │       │  │
│  │  └──────────────┘   │  └────────────────────┘       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐  │
│  │  LLM Service │  │Audio Service│  │WebSocket Manager │  │
│  │   (OpenAI)   │  │(TTS/STT)    │  │                  │  │
│  └──────────────┘  └─────────────┘  └──────────────────┘  │
└────────────┬──────────────────────────────┬─────────────────┘
             │                              │
             ▼                              ▼
┌─────────────────────┐      ┌──────────────────────────┐
│   PostgreSQL DB     │      │    Redis Cache           │
│  ┌───────────────┐  │      │  ┌────────────────────┐ │
│  │ Jobs          │  │      │  │ Session Data       │ │
│  │ Candidates    │  │      │  │ WebSocket Conns    │ │
│  │ Interviews    │  │      │  └────────────────────┘ │
│  │ DimensionScore│  │      └──────────────────────────┘
│  │ Reports       │  │
│  └───────────────┘  │
└─────────────────────┘
```

### Audio Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Voice Interview Flow                        │
└─────────────────────────────────────────────────────────────┘

1. CANDIDATE SPEECH INPUT
   │
   ├──> Browser: Web Speech API (SpeechRecognition)
   │    - Real-time speech-to-text
   │    - Language: English (en-US)
   │    - Continuous recognition mode
   │
   └──> Audio File Upload (Optional)
        - Format: WAV, MP3, WebM
        - Max size: 10MB
        ↓

2. SPEECH-TO-TEXT PROCESSING
   │
   ├──> Primary: OpenAI Whisper
   │    - Model: whisper-1
   │    - High accuracy transcription
   │    - Handles accents and background noise
   │    - Language auto-detection
   │
   └──> Fallback: Web Speech API
        - Browser-native
        - Lower latency
        - Privacy-focused (local processing)
        ↓

3. TEXT PROCESSING
   │
   └──> Backend API (FastAPI)
        - Receive transcribed text
        - Store in conversation history
        - Send to LLM for evaluation
        ↓

4. LLM EVALUATION (OpenAI GPT-4o-mini)
   │
   └──> Real-time Assessment
        - Analyze candidate response
        - Score across 6 dimensions
        - Collect evidence (quotes)
        - Generate follow-up question
        ↓

5. TEXT-TO-SPEECH SYNTHESIS
   │
   ├──> Primary: gTTS (Google Text-to-Speech)
   │    - Natural voice synthesis
   │    - Multiple language support
   │    - Cloud-based (requires internet)
   │
   ├──> Secondary: edge-tts (Microsoft Edge TTS)
   │    - High-quality voices
   │    - Fast synthesis
   │    - Free tier available
   │
   └──> Fallback: pyttsx3 (Offline)
        - Works without internet
        - Platform-native voices
        - Lower quality but reliable
        ↓

6. AUDIO PLAYBACK
   │
   └──> Browser: Web Audio API
        - Play synthesized response
        - Audio controls (pause/resume)
        - Volume adjustment
        - Queue management for multiple messages

┌─────────────────────────────────────────────────────────────┐
│                  Audio Quality Pipeline                      │
└─────────────────────────────────────────────────────────────┘

Input Audio → Noise Reduction → Transcription → Validation
                                      ↓
                              Error Handling
                                      ↓
                         Retry with Fallback Method
```

### Key Audio Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Speech Recognition** | Web Speech API + OpenAI Whisper | Convert candidate speech to text |
| **Text-to-Speech** | gTTS + edge-tts + pyttsx3 | Convert AI responses to speech |
| **Audio Processing** | ffmpeg + scipy + soundfile | Audio format conversion, noise reduction |
| **Audio Transport** | WebSocket + HTTP | Real-time audio streaming |
| **Audio Storage** | PostgreSQL + File System | Store audio files for review |

### Data Flow

1. **Interview Creation**: Admin creates job → Candidate applies → Interview scheduled
2. **Voice Interview**: Candidate starts interview → Voice → Backend → LLM → Response
3. **Real-Time Assessment**: Each answer → LLM Evaluation → Dimension scores updated
4. **Report Generation**: Interview complete → Aggregate scores → Generate comprehensive report

---

## 🔧 Prerequisites

### Required Software

- **Python**: 3.12 (required for audio features)
- **PostgreSQL**: 15 or higher
- **Redis**: 7 or higher (optional, for caching)
- **Node.js**: 18+ (for optional frontend tooling)

### API Keys

- **OpenAI API Key**: Required for LLM-based evaluation
  - Get from: https://platform.openai.com/api-keys
  - Model used: `gpt-4o-mini`

### System Requirements

- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB for application + database
- **Network**: Internet connection for OpenAI API calls

---

## 📦 Dependencies

### Backend (Python)

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
asyncpg==0.29.0
alembic==1.13.1
pydantic==2.5.3
pydantic-settings==2.1.0
python-multipart==0.0.6
openai==1.6.1
websockets==12.0
redis==5.0.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
pyyaml==6.0.1
structlog==24.1.0
pydub==0.25.1
```

### Frontend

- **Voice Interview**: Pure HTML/JavaScript with Web Speech API
- **Admin Portal**: Streamlit (optional)

---

## 🚀 Setup Instructions

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/iol-ai-interviewer-{your-name}.git
cd iol-ai-interviewer-{your-name}
```

### Step 2: Environment Configuration

1. **Copy the environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and add your credentials**:
   ```env
   # Database
   DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/ai_interviewer
   
   # OpenAI
   OPENAI_API_KEY=sk-your-openai-api-key-here
   
   # Application
   DEBUG=true
   LOG_LEVEL=INFO
   SECRET_KEY=your-secret-key-change-in-production
   ```

### Step 3: Database Setup

#### Option A: Using Docker (Recommended)

```bash
docker-compose up -d postgres redis
```

#### Option B: Local Installation

1. **Install PostgreSQL**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   
   # macOS
   brew install postgresql@15
   
   # Windows: Download from https://www.postgresql.org/download/
   ```

2. **Create database**:
   ```sql
   createdb ai_interviewer
   ```

3. **Install Redis** (optional):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   
   # macOS
   brew install redis
   
   # Windows: Download from https://redis.io/download
   ```

### Step 4: Backend Setup

1. **Create virtual environment**:
   ```bash
   cd backend
   python -m venv venv
   
   # Activate
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

4. **Initialize database** (optional - creates sample data):
   ```bash
   python init_db.py
   ```

### Step 5: Frontend Setup

No additional setup required - frontend uses vanilla HTML/JS.

---

## 🏃 Running Locally

### Option 1: Using Docker Compose (Easiest)

```bash
# Start all services
docker-compose up

# Access the application
# - Backend API: http://localhost:8001
# - API Docs: http://localhost:8001/docs
# - Voice Interview: http://localhost:8504/voice_interview.html
```

### Option 2: Manual Start

#### Terminal 1: Start Backend

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn app.main:app --reload --port 8001
```

#### Terminal 2: Start Frontend Server

```bash
cd frontend
python -m http.server 8504
```

#### Terminal 3: Start Admin Portal (Optional)

```bash
streamlit run admin_portal.py --server.port 8502
```

### Verify Installation

1. **Check Backend Health**:
   ```bash
   curl http://localhost:8001/health
   # Expected: {"status": "healthy", "version": "2.0.0"}
   ```

2. **Access API Documentation**:
   - Open: http://localhost:8001/docs
   - Interactive API explorer with all endpoints

3. **Start an Interview**:
   - Open: http://localhost:8504/voice_interview.html?interview_id=1
   - Click "Start Interview" and speak your answers

---

## 🎯 Usage Guide

### Creating a Job Posting

```bash
curl -X POST http://localhost:8001/api/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Backend Engineer",
    "department": "Engineering",
    "description": "We are seeking an experienced backend engineer",
    "requirements": ["5+ years Python", "FastAPI/Django", "PostgreSQL"],
    "location": "Remote",
    "job_type": "Full-time",
    "status": "active",
    "template_type": "backend-engineer"
  }'
```

### Creating a Candidate

```bash
curl -X POST http://localhost:8001/api/candidates/ \
  -F "job_id=1" \
  -F "first_name=John" \
  -F "last_name=Smith" \
  -F "email=john.smith@example.com" \
  -F "phone=+1-555-0123" \
  -F "resume=@resume.pdf"
```

### Creating an Interview

```bash
curl -X POST http://localhost:8001/api/interviews \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 1,
    "candidate_id": 1,
    "scheduled_at": "2026-01-15T10:00:00",
    "template_type": "backend-engineer"
  }'
```

### Conducting the Interview

1. Open the voice interview URL with the interview ID:
   ```
   http://localhost:8504/voice_interview.html?interview_id=1
   ```

2. Click **"Start Interview"**

3. The AI will ask questions - click the microphone button and speak your answers

4. Answer at least 3 questions to complete the interview

5. Click **"End Interview"** when done

### Generating Assessment Report

```bash
curl -X POST http://localhost:8001/api/interviews/1/report
```

The response includes:
- **Overall Recommendation**: Strong Hire / Hire / No Hire / Strong No Hire
- **Overall Score**: Weighted average across all dimensions (0-5 scale)
- **Dimension Scores**: Individual scores for each assessment dimension
- **Key Strengths**: Top 3 strong points with evidence
- **Areas of Concern**: Top 3 weaknesses with evidence
- **Notable Quotes**: Key candidate responses
- **Suggested Follow-ups**: Questions for next-round interviews
- **Summary**: Executive summary of performance
- **Full Transcript**: Complete conversation history

---

## 🚢 Deployment

### Deploying to Cloud Platforms

#### Option 1: Heroku

```bash
# Install Heroku CLI
# Create app
heroku create iol-ai-interviewer-{your-name}

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Set environment variables
heroku config:set OPENAI_API_KEY=your-key-here

# Deploy
git push heroku main
```

#### Option 2: AWS ECS

1. **Build Docker image**:
   ```bash
   docker build -t ai-interviewer-backend ./backend
   docker tag ai-interviewer-backend:latest your-ecr-repo/ai-interviewer:latest
   docker push your-ecr-repo/ai-interviewer:latest
   ```

2. **Create ECS Task Definition** with environment variables

3. **Deploy Service** with load balancer

#### Option 3: Railway.app

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Link to project
railway link

# Deploy
railway up
```

### Environment Variables for Production

```env
DEBUG=false
LOG_LEVEL=WARNING
SECRET_KEY=use-a-strong-random-key-here
DATABASE_URL=postgresql+asyncpg://prod-user:prod-pass@prod-host:5432/prod-db
OPENAI_API_KEY=sk-production-key
CORS_ORIGINS=["https://your-domain.com"]
```

---

## 📊 Assessment Framework

### Scoring System

- **Scale**: 1-5 (Poor, Fair, Good, Very Good, Excellent)
- **Dimensions**: 5 core competencies with different weights
- **Overall Score**: Weighted average of all dimensions
- **Recommendation Thresholds**:
  - **Strong Hire**: ≥ 4.3
  - **Hire**: 3.5 - 4.29
  - **No Hire**: 2.0 - 3.49
  - **Strong No Hire**: < 2.0

### Backend Engineer Assessment Dimensions

1. **Technical Knowledge** (30%)
   - Backend technologies
   - API design
   - Database expertise

2. **Problem-Solving** (25%)
   - Debugging approach
   - Troubleshooting methodology
   - Root cause analysis

3. **System Design** (20%)
   - Scalability considerations
   - Architectural decisions
   - Trade-off analysis

4. **Communication** (15%)
   - Clarity of explanation
   - Active listening
   - Collaboration mindset

5. **Code Quality** (10%)
   - Best practices
   - Testing approach
   - Maintainability focus

---

## 🧪 Testing

### Running Tests

```bash
# Backend unit tests
cd backend
pytest

# Integration tests
pytest tests/integration/

# E2E test
cd ..
./test-e2e.ps1
```

### Manual Testing Checklist

- [ ] Create job posting
- [ ] Add candidate with resume
- [ ] Schedule interview
- [ ] Complete voice interview (3+ questions)
- [ ] Generate assessment report
- [ ] Verify all dimension scores
- [ ] Check recommendation logic
- [ ] Export report data

---

## 📖 API Documentation

### Key Endpoints

#### Jobs
- `POST /api/jobs/` - Create job posting
- `GET /api/jobs/` - List all jobs
- `GET /api/jobs/{id}` - Get job details
- `PUT /api/jobs/{id}` - Update job

#### Candidates
- `POST /api/candidates/` - Create candidate
- `GET /api/candidates/` - List candidates
- `GET /api/candidates/{id}` - Get candidate details

#### Interviews
- `POST /api/interviews` - Create interview
- `POST /api/interviews/{id}/start` - Start interview
- `POST /api/interviews/{id}/answer` - Submit answer
- `POST /api/interviews/{id}/complete` - End interview
- `GET /api/interviews/{id}/assessment` - Get real-time scores
- `POST /api/interviews/{id}/report` - Generate comprehensive report

Full API documentation available at: http://localhost:8001/docs

---

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Code Style

- **Python**: Follow PEP 8 guidelines
- **Format**: Use `black` formatter
- **Linting**: Use `flake8`
- **Type Hints**: Use type annotations

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### MIT License Summary

- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use
- ❌ Liability
- ❌ Warranty

---

## 📞 Support

### Getting Help

- **Issues**: Open a GitHub issue for bugs or feature requests
- **Email**: [your-email@example.com]
- **Documentation**: See `/docs` folder for detailed guides

### Troubleshooting

**Problem**: Backend won't start
```bash
# Solution: Check PostgreSQL is running
psql -U postgres -c "SELECT version();"

# Check environment variables
cat .env
```

**Problem**: Voice not working
```bash
# Solution: Use Chrome or Edge browser
# Enable microphone permissions
# Check browser console for errors
```

**Problem**: OpenAI API errors
```bash
# Solution: Verify API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

## 👨‍💻 Author

**[Your Name]**
- GitHub: [@your-username](https://github.com/your-username)
- LinkedIn: [Your LinkedIn](https://linkedin.com/in/your-profile)
- Email: your-email@example.com

---

## 🙏 Acknowledgments

- **OpenAI** for GPT-4o-mini API
- **FastAPI** for the excellent web framework
- **Web Speech API** for voice capabilities
- **PostgreSQL** for reliable data storage

---

**Built with ❤️ for IOL AI Fellowship**

