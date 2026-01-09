"""
Pydantic schemas for Job management
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============================================================================
# JOB SCHEMAS
# ============================================================================

class JobBase(BaseModel):
    """Base job schema"""
    title: str = Field(..., min_length=3, max_length=255)
    department: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[str] = Field(None, max_length=50)  # Full-time, Part-time, Contract
    experience_level: Optional[str] = Field(None, max_length=50)  # Junior, Mid, Senior
    
    description: str = Field(..., min_length=50)
    responsibilities: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    nice_to_have: List[str] = Field(default_factory=list)
    
    interview_template: str = Field(default="backend-engineer", max_length=100)
    interview_duration_minutes: int = Field(default=60, ge=15, le=180)
    custom_questions: List[str] = Field(default_factory=list)


class JobCreate(JobBase):
    """Schema for creating a job"""
    status: str = Field(default="active")  # Default to active for new jobs


class JobUpdate(BaseModel):
    """Schema for updating a job"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    department: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    
    description: Optional[str] = Field(None, min_length=50)
    responsibilities: Optional[List[str]] = None
    requirements: Optional[List[str]] = None
    nice_to_have: Optional[List[str]] = None
    
    interview_template: Optional[str] = None
    interview_duration_minutes: Optional[int] = Field(None, ge=15, le=180)
    custom_questions: Optional[List[str]] = None
    
    status: Optional[str] = None  # draft, active, paused, closed


class JobResponse(JobBase):
    """Schema for job response"""
    id: int
    status: str
    posted_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    
    # Computed fields
    candidate_count: int = 0
    active_interview_count: int = 0
    
    class Config:
        from_attributes = True


class JobSummary(BaseModel):
    """Minimal job schema for listings"""
    id: int
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    status: str
    posted_at: Optional[datetime] = None
    candidate_count: int = 0
    
    class Config:
        from_attributes = True


class JobPublic(BaseModel):
    """Public-facing job schema (for candidate portal)"""
    id: int
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    description: str
    responsibilities: List[str]
    requirements: List[str]
    nice_to_have: List[str]
    posted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# CANDIDATE SCHEMAS
# ============================================================================

class CandidateBase(BaseModel):
    """Base candidate schema"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    cover_letter: Optional[str] = None


class CandidateCreate(CandidateBase):
    """Schema for creating a candidate"""
    job_id: int


class CandidateUpdate(BaseModel):
    """Schema for updating a candidate"""
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    status: Optional[str] = None  # applied, interview_scheduled, etc.


class CandidateResponse(CandidateBase):
    """Schema for candidate response"""
    id: int
    job_id: int
    status: str
    resume_filename: str
    resume_path: str
    applied_at: datetime
    updated_at: datetime
    
    # Related data
    job_title: Optional[str] = None
    interview_count: int = 0
    
    class Config:
        from_attributes = True


class CandidateSummary(BaseModel):
    """Minimal candidate schema for listings"""
    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    job_id: int
    job_title: Optional[str] = None
    status: str
    applied_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# INTERVIEW SCHEMAS (Enhanced for Phase 2)
# ============================================================================

class InterviewCreate(BaseModel):
    """Schema for creating an interview"""
    job_id: int
    candidate_id: int
    template_name: Optional[str] = None  # If None, use job's template
    scheduled_date: Optional[datetime] = None
    interview_format: Optional[str] = None  # video, audio, phone, text
    meeting_link: Optional[str] = None


class InterviewResponse(BaseModel):
    """Schema for interview response"""
    id: int
    session_id: str
    job_id: int
    candidate_id: int
    template_name: str
    scheduled_date: Optional[datetime] = None
    interview_format: Optional[str] = None
    meeting_link: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    current_question_index: int
    created_at: datetime
    
    # Related data
    job_title: Optional[str] = None
    candidate_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class InterviewDetail(InterviewResponse):
    """Detailed interview response with conversation"""
    conversation_history: List[dict] = []
    job_context: Optional[dict] = None
    candidate_context: Optional[dict] = None


class InterviewMessage(BaseModel):
    """Schema for interview message exchange"""
    message: str = Field(..., min_length=1, max_length=5000)


class InterviewMessageResponse(BaseModel):
    """Schema for interview AI response"""
    response: str
    is_complete: bool = False
    question_number: int
    total_questions: int


# ============================================================================
# UTILITY SCHEMAS
# ============================================================================

class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    environment: str
    services: dict


class PaginatedResponse(BaseModel):
    """Generic paginated response"""
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
