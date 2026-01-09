"""
Main FastAPI application for Phase 2
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.redis import close_redis
from app.core.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("app_startup", version=settings.app_version, environment=settings.environment)
    
    # Create upload directories
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.reports_storage_path, exist_ok=True)
    os.makedirs(settings.transcripts_storage_path, exist_ok=True)
    logger.info("storage_directories_created")
    
    # Initialize database
    await init_db()
    logger.info("database_initialized")
    
    yield
    
    # Shutdown
    logger.info("app_shutdown")
    await close_db()
    await close_redis()
    logger.info("cleanup_complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-Assisted Technical Interviewer - Phase 2 Multi-User System",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods including OPTIONS
    allow_headers=["*"],  # Allow all headers
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "features": [
            "Job Management",
            "Candidate Applications",
            "AI-Powered Interviews",
            "Automated Reports"
        ]
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "services": {
            "database": "connected",
            "redis": "connected",
            "llm": f"{settings.llm_provider}"
        }
    }


# Import and include routers
from app.api import jobs, candidates, interviews, websocket, audio

app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(candidates.router, prefix="/api/candidates", tags=["Candidates"])
app.include_router(interviews.router, prefix="/api/interviews", tags=["Interviews"])
app.include_router(websocket.router, tags=["WebSocket"])
app.include_router(audio.router, prefix="/api/audio", tags=["Audio"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
