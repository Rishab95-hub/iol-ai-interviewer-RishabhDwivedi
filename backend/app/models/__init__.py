"""
Database models for Phase 2: Jobs, Candidates, and enhanced Interviews
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, 
    JSON, Enum as SQLEnum, ForeignKey
)
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class JobStatus(str, enum.Enum):
    """Job posting status"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class CandidateStatus(str, enum.Enum):
    """Candidate application status"""
    APPLIED = "applied"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_IN_PROGRESS = "interview_in_progress"
    INTERVIEW_COMPLETED = "interview_completed"
    UNDER_REVIEW = "under_review"
    REJECTED = "rejected"
    ACCEPTED = "accepted"


class InterviewStatus(str, enum.Enum):
    """Interview status enum"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class RecommendationType(str, enum.Enum):
    """Hiring recommendation enum"""
    STRONG_HIRE = "strong_hire"
    HIRE = "hire"
    NO_HIRE = "no_hire"
    STRONG_NO_HIRE = "strong_no_hire"


# ============================================================================
# MODELS
# ============================================================================

class Job(Base):
    """Job posting model"""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Job Details
    title = Column(String(255), nullable=False, index=True)
    department = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    job_type = Column(String(50), nullable=True)  # Full-time, Part-time, Contract
    experience_level = Column(String(50), nullable=True)  # Junior, Mid, Senior
    
    # Job Description
    description = Column(Text, nullable=False)
    responsibilities = Column(JSON, default=list)  # List of responsibility strings
    requirements = Column(JSON, default=list)  # List of requirement strings
    nice_to_have = Column(JSON, default=list)  # List of nice-to-have skills
    
    # Interview Configuration
    interview_template = Column(String(100), nullable=False)  # e.g., "backend-engineer"
    interview_duration_minutes = Column(Integer, default=60)
    custom_questions = Column(JSON, default=list)  # Additional custom questions
    
    # Status
    status = Column(SQLEnum(JobStatus), nullable=False, index=True)
    posted_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)  # Admin user ID
    
    # Relationships
    candidates = relationship("Candidate", back_populates="job")
    interviews = relationship("Interview", back_populates="job")


class Candidate(Base):
    """Candidate application model"""
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    
    # Resume
    resume_filename = Column(String(500), nullable=False)
    resume_path = Column(String(1000), nullable=False)
    resume_text = Column(Text, nullable=True)  # Extracted text for AI context
    
    # Application
    status = Column(SQLEnum(CandidateStatus), default=CandidateStatus.APPLIED, index=True)
    cover_letter = Column(Text, nullable=True)
    
    # Metadata
    applied_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="candidates")
    interviews = relationship("Interview", back_populates="candidate")


class Interview(Base):
    """Interview session model - Enhanced for Phase 2"""
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    
    # References
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    
    # Interview Configuration
    template_name = Column(String(100), nullable=False)
    template_version = Column(String(20), default="1.0")
    
    # Scheduling
    scheduled_date = Column(DateTime, nullable=True)  # When interview is scheduled for
    interview_format = Column(String(20), nullable=True)  # 'video', 'audio', 'phone'
    meeting_link = Column(String(500), nullable=True)  # Video call link if applicable
    
    # Status and Timing
    status = Column(SQLEnum(InterviewStatus), default=InterviewStatus.PENDING, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Interview Data
    conversation_history = Column(JSON, default=list)  # List of messages
    current_question_index = Column(Integer, default=0)
    
    # Context (stored for AI)
    job_context = Column(JSON, nullable=True)  # Snapshot of job details
    candidate_context = Column(JSON, nullable=True)  # Snapshot of candidate resume
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    
    # Relationships
    job = relationship("Job", back_populates="interviews")
    candidate = relationship("Candidate", back_populates="interviews")
    report = relationship("InterviewReport", back_populates="interview", uselist=False)
    scores = relationship("DimensionScore", back_populates="interview")


class InterviewReport(Base):
    """Generated interview report model"""
    __tablename__ = "interview_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), unique=True)
    
    # Overall Assessment
    recommendation = Column(SQLEnum(RecommendationType), nullable=False)
    overall_score = Column(Float, nullable=False)  # Average of all dimensions
    
    # Summary Sections
    key_strengths = Column(JSON, default=list)  # List of strength points
    areas_of_concern = Column(JSON, default=list)  # List of concerns
    notable_quotes = Column(JSON, default=list)  # List of candidate quotes
    suggested_follow_ups = Column(JSON, default=list)  # Follow-up questions
    
    # Transcript
    full_transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    
    # Report Metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    report_version = Column(String(20), default="1.0")
    
    # File References
    pdf_path = Column(String(500), nullable=True)
    json_path = Column(String(500), nullable=True)
    
    # Relationships
    interview = relationship("Interview", back_populates="report")


class DimensionScore(Base):
    """Individual dimension scores for interview"""
    __tablename__ = "dimension_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    
    # Score Details
    dimension_name = Column(String(100), nullable=False)  # e.g., "Technical Knowledge"
    score = Column(Float, nullable=False)
    max_score = Column(Float, default=5.0)
    
    # Supporting Information
    reasoning = Column(Text, nullable=True)
    evidence = Column(JSON, default=list)  # List of quote/example strings
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    interview = relationship("Interview", back_populates="scores")
