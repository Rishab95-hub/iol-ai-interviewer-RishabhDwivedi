"""
Candidates API endpoints for candidate management and resume processing
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import os
import uuid
import aiofiles

from app.core.database import get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.models import Candidate, Job, Interview, CandidateStatus, JobStatus
from app.schemas.models import (
    CandidateCreate, CandidateUpdate, CandidateResponse, CandidateSummary
)
from app.services.resume_processor import (
    extract_resume_text, validate_resume_file, sanitize_filename
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    job_id: int = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    cover_letter: Optional[str] = Form(None),
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new candidate with resume upload
    
    - **job_id**: ID of the job being applied to
    - **first_name**: Candidate's first name
    - **last_name**: Candidate's last name
    - **email**: Candidate's email address
    - **resume**: Resume file (PDF, DOCX, or TXT)
    """
    logger.info("candidate_create_request", job_id=job_id, email=email)
    
    # Validate job exists and is active
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    if job.status != JobStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not active. Current status: {job.status}"
        )
    
    # Check if candidate already applied to this job
    existing = await db.execute(
        select(Candidate).where(
            Candidate.job_id == job_id,
            Candidate.email == email
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied to this job"
        )
    
    # Validate resume file
    file_size = 0
    content = await resume.read()
    file_size = len(content)
    await resume.seek(0)  # Reset file pointer
    
    is_valid, error_msg = validate_resume_file(
        resume.filename,
        file_size,
        settings.allowed_resume_formats,
        settings.max_resume_size_bytes
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Save resume file
    sanitized_filename = sanitize_filename(resume.filename)
    unique_filename = f"{uuid.uuid4()}_{sanitized_filename}"
    resume_dir = settings.upload_dir
    os.makedirs(resume_dir, exist_ok=True)
    resume_path = os.path.join(resume_dir, unique_filename)
    
    try:
        async with aiofiles.open(resume_path, 'wb') as f:
            await f.write(content)
        
        logger.info("resume_saved", path=resume_path, size=file_size)
        
        # Extract text from resume
        try:
            resume_text = extract_resume_text(resume_path, resume.filename)
            logger.info("resume_text_extracted", length=len(resume_text))
        except Exception as e:
            logger.error("resume_extraction_failed", error=str(e))
            # Don't fail the application, just log the error
            resume_text = f"[Text extraction failed: {str(e)}]"
        
        # Create candidate record
        candidate = Candidate(
            job_id=job_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            linkedin_url=linkedin_url,
            cover_letter=cover_letter,
            resume_filename=resume.filename,
            resume_path=resume_path,
            resume_text=resume_text,
            status=CandidateStatus.APPLIED,
            applied_at=datetime.utcnow()
        )
        
        db.add(candidate)
        await db.commit()
        await db.refresh(candidate)
        
        logger.info("candidate_created", candidate_id=candidate.id, job_id=job_id)
        
        # Build response
        response = CandidateResponse.model_validate(candidate)
        response.job_title = job.title
        response.interview_count = 0
        
        return response
        
    except Exception as e:
        # Clean up file if database operation fails
        if os.path.exists(resume_path):
            os.remove(resume_path)
        logger.error("candidate_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create candidate: {str(e)}"
        )


@router.get("/", response_model=List[CandidateSummary])
async def list_candidates(
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List all candidates
    
    - **job_id**: Filter by specific job
    - **status**: Filter by candidate status
    - **skip**: Pagination offset
    - **limit**: Maximum results to return
    """
    logger.info("candidate_list_request", job_id=job_id, status_filter=status)
    
    # Build query
    query = select(Candidate).join(Job, Candidate.job_id == Job.id)
    
    if job_id:
        query = query.where(Candidate.job_id == job_id)
    
    if status:
        try:
            candidate_status = CandidateStatus(status)
            query = query.where(Candidate.status == candidate_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    query = query.order_by(Candidate.applied_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    candidates = result.scalars().all()
    
    # Build summaries with job titles
    summaries = []
    for candidate in candidates:
        # Get job title
        job_result = await db.execute(select(Job.title).where(Job.id == candidate.job_id))
        job_title = job_result.scalar()
        
        summary = CandidateSummary.model_validate(candidate)
        summary.job_title = job_title
        summaries.append(summary)
    
    logger.info("candidate_list_response", count=len(summaries))
    return summaries


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get candidate details by ID
    """
    logger.info("candidate_get_request", candidate_id=candidate_id)
    
    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    
    if not candidate:
        logger.warning("candidate_not_found", candidate_id=candidate_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found"
        )
    
    # Get job title
    job_result = await db.execute(select(Job.title).where(Job.id == candidate.job_id))
    job_title = job_result.scalar()
    
    # Get interview count
    interview_count_query = select(func.count(Interview.id)).where(
        Interview.candidate_id == candidate_id
    )
    interview_count_result = await db.execute(interview_count_query)
    interview_count = interview_count_result.scalar() or 0
    
    response = CandidateResponse.model_validate(candidate)
    response.job_title = job_title
    response.interview_count = interview_count
    
    logger.info("candidate_get_response", candidate_id=candidate_id)
    return response


@router.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: int,
    candidate_data: CandidateUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update candidate information
    
    Note: Cannot update resume through this endpoint. Status updates are typically
    done automatically by the system.
    """
    logger.info("candidate_update_request", candidate_id=candidate_id)
    
    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found"
        )
    
    # Update fields
    update_data = candidate_data.model_dump(exclude_unset=True)
    
    if "status" in update_data:
        new_status = update_data["status"]
        try:
            candidate.status = CandidateStatus(new_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {new_status}"
            )
        del update_data["status"]
    
    for field, value in update_data.items():
        setattr(candidate, field, value)
    
    candidate.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(candidate)
    
    logger.info("candidate_updated", candidate_id=candidate_id)
    
    # Get job title
    job_result = await db.execute(select(Job.title).where(Job.id == candidate.job_id))
    job_title = job_result.scalar()
    
    response = CandidateResponse.model_validate(candidate)
    response.job_title = job_title
    response.interview_count = 0
    
    return response


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a candidate
    
    Note: This will fail if there are associated interviews.
    Consider updating status instead.
    """
    logger.info("candidate_delete_request", candidate_id=candidate_id)
    
    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found"
        )
    
    # Check for associated interviews
    interview_count_query = select(func.count(Interview.id)).where(
        Interview.candidate_id == candidate_id
    )
    interview_count_result = await db.execute(interview_count_query)
    interview_count = interview_count_result.scalar() or 0
    
    if interview_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete candidate with {interview_count} associated interviews"
        )
    
    # Delete resume file
    if os.path.exists(candidate.resume_path):
        try:
            os.remove(candidate.resume_path)
            logger.info("resume_file_deleted", path=candidate.resume_path)
        except Exception as e:
            logger.error("resume_deletion_failed", error=str(e))
    
    await db.delete(candidate)
    await db.commit()
    
    logger.info("candidate_deleted", candidate_id=candidate_id)
    return None


@router.get("/{candidate_id}/resume-text")
async def get_candidate_resume_text(
    candidate_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the extracted resume text for a candidate
    """
    logger.info("candidate_resume_text_request", candidate_id=candidate_id)
    
    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found"
        )
    
    return {
        "candidate_id": candidate_id,
        "resume_filename": candidate.resume_filename,
        "resume_text": candidate.resume_text,
        "text_length": len(candidate.resume_text) if candidate.resume_text else 0
    }
