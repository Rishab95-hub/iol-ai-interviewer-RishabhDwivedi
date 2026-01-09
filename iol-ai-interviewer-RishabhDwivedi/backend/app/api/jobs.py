"""
Jobs API endpoints for job management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime

from app.core.database import get_db
from app.core.logging import get_logger
from app.models import Job, Candidate, Interview, JobStatus
from app.schemas.models import (
    JobCreate, JobUpdate, JobResponse, JobSummary, JobPublic, PaginatedResponse
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new job posting
    
    - **title**: Job title (required)
    - **description**: Detailed job description (required)
    - **requirements**: List of job requirements
    - **interview_template**: Template to use for interviews
    """
    logger.info("job_create_request", title=job_data.title)
    
    # Create job instance
    job = Job(
        **job_data.model_dump(),
        created_at=datetime.utcnow()
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    logger.info("job_created", job_id=job.id, title=job.title)
    
    # Build response
    response = JobResponse.model_validate(job)
    response.candidate_count = 0
    response.active_interview_count = 0
    
    return response


@router.get("/", response_model=List[JobSummary])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List all job postings
    
    - **status**: Filter by job status (draft, active, paused, closed)
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    logger.info("job_list_request", status_filter=status)
    
    # Build query
    query = select(Job)
    
    if status:
        try:
            job_status = JobStatus(status)
            query = query.where(Job.status == job_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    query = query.order_by(Job.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    # Build summaries with counts
    summaries = []
    for job in jobs:
        # Get candidate count
        candidate_count_query = select(func.count(Candidate.id)).where(Candidate.job_id == job.id)
        candidate_count_result = await db.execute(candidate_count_query)
        candidate_count = candidate_count_result.scalar() or 0
        
        summary = JobSummary.model_validate(job)
        summary.candidate_count = candidate_count
        summaries.append(summary)
    
    logger.info("job_list_response", count=len(summaries))
    return summaries


@router.get("/public", response_model=List[JobPublic])
async def list_public_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    List active job postings (public endpoint for candidate portal)
    
    Only returns jobs with status=active
    """
    logger.info("job_list_public_request")
    
    query = (
        select(Job)
        .where(Job.status == JobStatus.ACTIVE)
        .order_by(Job.posted_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    public_jobs = [JobPublic.model_validate(job) for job in jobs]
    
    logger.info("job_list_public_response", count=len(public_jobs))
    return public_jobs


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific job by ID
    """
    logger.info("job_get_request", job_id=job_id)
    
    # Get job
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        logger.warning("job_not_found", job_id=job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Get counts
    candidate_count_query = select(func.count(Candidate.id)).where(Candidate.job_id == job_id)
    candidate_count_result = await db.execute(candidate_count_query)
    candidate_count = candidate_count_result.scalar() or 0
    
    active_interview_count_query = select(func.count(Interview.id)).where(
        and_(
            Interview.job_id == job_id,
            Interview.status.in_(["pending", "in_progress"])
        )
    )
    active_interview_count_result = await db.execute(active_interview_count_query)
    active_interview_count = active_interview_count_result.scalar() or 0
    
    response = JobResponse.model_validate(job)
    response.candidate_count = candidate_count
    response.active_interview_count = active_interview_count
    
    logger.info("job_get_response", job_id=job_id, title=job.title)
    return response


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_data: JobUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a job posting
    """
    logger.info("job_update_request", job_id=job_id)
    
    # Get job
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        logger.warning("job_not_found", job_id=job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Update fields
    update_data = job_data.model_dump(exclude_unset=True)
    
    # Handle status changes
    if "status" in update_data:
        new_status = update_data["status"]
        try:
            job.status = JobStatus(new_status)
            # Set posted_at if transitioning to active
            if job.status == JobStatus.ACTIVE and not job.posted_at:
                job.posted_at = datetime.utcnow()
            # Set closed_at if transitioning to closed
            elif job.status == JobStatus.CLOSED and not job.closed_at:
                job.closed_at = datetime.utcnow()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {new_status}"
            )
        del update_data["status"]
    
    # Update other fields
    for field, value in update_data.items():
        setattr(job, field, value)
    
    job.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(job)
    
    logger.info("job_updated", job_id=job_id)
    
    response = JobResponse.model_validate(job)
    response.candidate_count = 0
    response.active_interview_count = 0
    
    return response


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a job posting
    
    Note: This will fail if there are associated candidates or interviews.
    Consider setting status to 'closed' instead.
    """
    logger.info("job_delete_request", job_id=job_id)
    
    # Get job
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        logger.warning("job_not_found", job_id=job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Check for associated candidates
    candidate_count_query = select(func.count(Candidate.id)).where(Candidate.job_id == job_id)
    candidate_count_result = await db.execute(candidate_count_query)
    candidate_count = candidate_count_result.scalar() or 0
    
    if candidate_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete job with {candidate_count} associated candidates. Set status to 'closed' instead."
        )
    
    await db.delete(job)
    await db.commit()
    
    logger.info("job_deleted", job_id=job_id)
    return None


@router.post("/{job_id}/publish", response_model=JobResponse)
async def publish_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Publish a job posting (change status from draft to active)
    """
    logger.info("job_publish_request", job_id=job_id)
    
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job.status = JobStatus.ACTIVE
    job.posted_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(job)
    
    logger.info("job_published", job_id=job_id)
    
    response = JobResponse.model_validate(job)
    response.candidate_count = 0
    response.active_interview_count = 0
    
    return response


@router.post("/{job_id}/close", response_model=JobResponse)
async def close_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Close a job posting
    """
    logger.info("job_close_request", job_id=job_id)
    
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job.status = JobStatus.CLOSED
    job.closed_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(job)
    
    logger.info("job_closed", job_id=job_id)
    
    response = JobResponse.model_validate(job)
    return response
