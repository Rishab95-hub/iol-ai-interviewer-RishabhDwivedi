"""
Enhanced Interview API for Phase 2 with job and candidate context
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import attributes
from datetime import datetime
import uuid

from app.core.database import get_db
from app.core.logging import get_logger
from app.models import Interview, Job, Candidate, InterviewStatus, CandidateStatus, DimensionScore
from app.schemas.models import (
    InterviewCreate, InterviewResponse, InterviewDetail, 
    InterviewMessage, InterviewMessageResponse
)
from app.schemas.assessment import (
    DimensionScoreResponse, ComprehensiveReport,
    AssessmentProgress
)
from app.services.llm_service import llm_service
from app.services.assessment_service import AssessmentService

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def create_interview(
    interview_data: InterviewCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new interview session
    
    - **job_id**: ID of the job position
    - **candidate_id**: ID of the candidate
    - **template_name**: Optional override for interview template
    """
    logger.info("interview_create_request", 
               job_id=interview_data.job_id, 
               candidate_id=interview_data.candidate_id)
    
    # Get job
    job_result = await db.execute(select(Job).where(Job.id == interview_data.job_id))
    job = job_result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {interview_data.job_id} not found"
        )
    
    # Get candidate
    candidate_result = await db.execute(
        select(Candidate).where(Candidate.id == interview_data.candidate_id)
    )
    candidate = candidate_result.scalar_one_or_none()
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {interview_data.candidate_id} not found"
        )
    
    # Verify candidate applied to this job
    if candidate.job_id != job.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate did not apply to this job"
        )
    
    # Use job's template if not specified
    template_name = interview_data.template_name or job.interview_template
    
    # Create job context snapshot
    job_context = {
        "title": job.title,
        "department": job.department,
        "description": job.description,
        "requirements": job.requirements,
        "responsibilities": job.responsibilities,
        "experience_level": job.experience_level
    }
    
    # Create candidate context snapshot (with resume excerpt)
    resume_excerpt = candidate.resume_text[:3000] if candidate.resume_text else "[Resume not available]"
    candidate_context = {
        "name": f"{candidate.first_name} {candidate.last_name}",
        "email": candidate.email,
        "resume_excerpt": resume_excerpt,
        "linkedin_url": candidate.linkedin_url
    }
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Create interview
    interview = Interview(
        session_id=session_id,
        job_id=job.id,
        candidate_id=candidate.id,
        template_name=template_name,
        scheduled_date=interview_data.scheduled_date,
        interview_format=interview_data.interview_format,
        meeting_link=interview_data.meeting_link,
        status=InterviewStatus.PENDING,
        conversation_history=[],
        job_context=job_context,
        candidate_context=candidate_context,
        created_at=datetime.utcnow()
    )
    
    db.add(interview)
    
    # Update candidate status
    candidate.status = CandidateStatus.INTERVIEW_SCHEDULED
    candidate.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(interview)
    
    logger.info("interview_created", interview_id=interview.id, session_id=session_id)
    
    response = InterviewResponse.model_validate(interview)
    response.job_title = job.title
    response.candidate_name = f"{candidate.first_name} {candidate.last_name}"
    
    return response


@router.post("/{interview_id}/start", response_model=InterviewMessageResponse)
async def start_interview(
    interview_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Start an interview and receive the first question
    """
    logger.info("interview_start_request", interview_id=interview_id)
    
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found"
        )
    
    if interview.status != InterviewStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Interview already started. Current status: {interview.status}"
        )
    
    # Update status
    interview.status = InterviewStatus.IN_PROGRESS
    interview.started_at = datetime.utcnow()
    
    # Update candidate status
    candidate_result = await db.execute(
        select(Candidate).where(Candidate.id == interview.candidate_id)
    )
    candidate = candidate_result.scalar_one()
    candidate.status = CandidateStatus.INTERVIEW_IN_PROGRESS
    
    # Get job details
    job_result = await db.execute(select(Job).where(Job.id == interview.job_id))
    job = job_result.scalar_one()
    
    # Build context-aware system prompt
    job_req_text = "\n".join(f"- {req}" for req in job.requirements) if job.requirements else ""
    job_resp_text = "\n".join(f"- {resp}" for resp in job.responsibilities) if job.responsibilities else ""
    
    system_prompt = f"""You are an expert technical interviewer conducting an interview for the position of {job.title}.

JOB DETAILS:
- Title: {job.title}
- Department: {job.department or 'Not specified'}
- Experience Level: {job.experience_level or 'Not specified'}
- Description: {job.description[:500]}...

KEY REQUIREMENTS:
{job_req_text}

KEY RESPONSIBILITIES:
{job_resp_text}

CANDIDATE INFORMATION:
- Name: {interview.candidate_context.get('name')}
- Resume highlights: {interview.candidate_context.get('resume_excerpt', '')[:500]}...

Your task is to conduct a thorough technical interview with approximately 8-10 questions. Assess:
1. Technical knowledge relevant to the job requirements
2. Problem-solving abilities
3. Communication skills
4. Cultural fit and motivation
5. Depth of experience mentioned in their resume

IMPORTANT: 
- Ask ONE question at a time
- Do NOT role-play or simulate the candidate's answers
- Wait for the candidate to respond before asking the next question
- Keep questions conversational but professional
- Build on their previous answers

Start with a welcoming opening question about their background that ties to the job requirements.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Please ask your first interview question."}
    ]
    
    # Generate first question
    first_question = await llm_service.generate_response(
        messages,
        temperature=0.7,
        max_tokens=300
    )
    
    # Save conversation
    interview.conversation_history = [
        {
            "role": "assistant",
            "content": first_question,
            "timestamp": datetime.utcnow().isoformat(),
            "question_number": 1
        }
    ]
    attributes.flag_modified(interview, "conversation_history")
    interview.current_question_index = 1
    
    await db.commit()
    
    # Initialize assessment dimensions
    assessment_service = AssessmentService(db, llm_service)
    assessment_service.initialize_dimensions(interview.id, interview.template_name)
    
    logger.info("interview_started", interview_id=interview_id)
    
    return InterviewMessageResponse(
        response=first_question,
        is_complete=False,
        question_number=1,
        total_questions=10
    )


@router.post("/{interview_id}/respond", response_model=InterviewMessageResponse)
async def respond_to_interview(
    interview_id: int,
    message: InterviewMessage,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a candidate response and receive the next question
    """
    logger.info("interview_respond_request", interview_id=interview_id)
    
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found"
        )
    
    if interview.status != InterviewStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Interview not in progress. Current status: {interview.status}"
        )
    
    # Get the current question from history
    current_question = ""
    for msg in reversed(interview.conversation_history):
        if msg["role"] == "assistant":
            current_question = msg["content"]
            break
    
    # Add candidate response to history
    interview.conversation_history.append({
        "role": "user",
        "content": message.message,
        "timestamp": datetime.utcnow().isoformat(),
        "question_number": interview.current_question_index
    })
    attributes.flag_modified(interview, "conversation_history")
    
    # Evaluate answer in real-time
    assessment_service = AssessmentService(db, llm_service)
    try:
        evaluation = await assessment_service.evaluate_answer(
            interview_id=interview.id,
            question=current_question,
            answer=message.message,
            question_number=interview.current_question_index
        )
        logger.info("answer_evaluated", 
                   interview_id=interview_id,
                   dimensions_updated=len(evaluation.scores))
    except Exception as e:
        logger.error(f"Failed to evaluate answer: {e}", interview_id=interview_id)
        # Continue even if evaluation fails
    
    # Check if interview should end (after 10 questions)
    if interview.current_question_index >= 10:
        interview.status = InterviewStatus.COMPLETED
        interview.completed_at = datetime.utcnow()
        duration = (interview.completed_at - interview.started_at).total_seconds()
        interview.duration_seconds = int(duration)
        
        # Update candidate status
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.id == interview.candidate_id)
        )
        candidate = candidate_result.scalar_one()
        candidate.status = CandidateStatus.INTERVIEW_COMPLETED
        candidate.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info("interview_completed", interview_id=interview_id, duration=duration)
        
        return InterviewMessageResponse(
            response="Thank you for your time! The interview is now complete. We'll review your responses and get back to you soon.",
            is_complete=True,
            question_number=interview.current_question_index,
            total_questions=10
        )
    
    # Build context for next question
    job_req_text = "\n".join(f"- {req}" for req in interview.job_context.get('requirements', [])) if interview.job_context.get('requirements') else ""
    
    system_prompt = f"""You are conducting a technical interview for {interview.job_context.get('title')}.

JOB REQUIREMENTS:
{job_req_text}

CANDIDATE RESUME HIGHLIGHTS:
{interview.candidate_context.get('resume_excerpt', '')[:500]}...

Based on the conversation so far, ask the next relevant question to assess:
- Technical knowledge and skills
- Problem-solving approach
- Experience depth
- Communication clarity
- Fit for the role

Make the question natural and conversational, building on their previous answers.
Ask follow-up questions if their previous answer was interesting or needs clarification.
"""

    # Build message history for LLM
    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in interview.conversation_history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    # Generate next question
    next_question = await llm_service.generate_response(
        messages,
        temperature=0.8,
        max_tokens=300
    )
    
    # Save AI question
    interview.current_question_index += 1
    interview.conversation_history.append({
        "role": "assistant",
        "content": next_question,
        "timestamp": datetime.utcnow().isoformat(),
        "question_number": interview.current_question_index
    })
    attributes.flag_modified(interview, "conversation_history")
    
    await db.commit()
    
    logger.info("interview_response_generated", 
               interview_id=interview_id,
               question_number=interview.current_question_index)
    
    return InterviewMessageResponse(
        response=next_question,
        is_complete=False,
        question_number=interview.current_question_index,
        total_questions=10
    )


@router.post("/{interview_id}/end", response_model=InterviewResponse)
async def end_interview(
    interview_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually end an interview early
    """
    logger.info("interview_end_request", interview_id=interview_id)
    
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found"
        )
    
    if interview.status == InterviewStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview already completed"
        )
    
    # Mark as completed
    interview.status = InterviewStatus.COMPLETED
    interview.completed_at = datetime.utcnow()
    
    if interview.started_at:
        duration = (interview.completed_at - interview.started_at).total_seconds()
        interview.duration_seconds = int(duration)
    
    # Update candidate status
    candidate_result = await db.execute(
        select(Candidate).where(Candidate.id == interview.candidate_id)
    )
    candidate = candidate_result.scalar_one()
    candidate.status = CandidateStatus.INTERVIEW_COMPLETED
    candidate.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(interview)
    
    logger.info("interview_ended", interview_id=interview_id)
    
    # Get related data
    job_result = await db.execute(select(Job).where(Job.id == interview.job_id))
    job = job_result.scalar_one()
    
    response = InterviewResponse.model_validate(interview)
    response.job_title = job.title
    response.candidate_name = interview.candidate_context.get('name')
    
    return response


@router.post("/{interview_id}/answer")
async def submit_answer(
    interview_id: int,
    answer_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Simplified endpoint for submitting answers (for Streamlit interface)
    """
    answer = answer_data.get("answer", "").strip()
    
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answer cannot be empty"
        )
    
    # Get interview
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found"
        )
    
    if interview.status != InterviewStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Interview is not in progress. Status: {interview.status}"
        )
    
    # Add candidate answer to conversation
    interview.conversation_history.append({
        "role": "user",
        "content": answer,
        "timestamp": datetime.utcnow().isoformat(),
        "question_number": interview.current_question_index
    })
    
    # Get job details to rebuild system prompt
    job_result = await db.execute(select(Job).where(Job.id == interview.job_id))
    job = job_result.scalar_one()
    
    # Build context-aware system prompt
    job_req_text = "\n".join(f"- {req}" for req in job.requirements) if job.requirements else ""
    job_resp_text = "\n".join(f"- {resp}" for resp in job.responsibilities) if job.responsibilities else ""
    
    system_prompt = f"""You are an expert technical interviewer conducting an interview for the position of {job.title}.

JOB DETAILS:
- Title: {job.title}
- Department: {job.department or 'Not specified'}
- Experience Level: {job.experience_level or 'Not specified'}

KEY REQUIREMENTS:
{job_req_text}

CANDIDATE INFORMATION:
- Name: {interview.candidate_context.get('name')}

Your task is to conduct a thorough technical interview with approximately 8-10 questions. Assess technical knowledge, problem-solving abilities, and communication skills.

IMPORTANT:
- Ask ONE question at a time
- Do NOT role-play or simulate the candidate's answers
- Wait for the candidate to respond
- Build on their previous answers with relevant follow-up questions
- Keep questions conversational but professional"""
    
    # Generate next question using the singleton llm_service
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    messages.extend([
        {"role": msg["role"], "content": msg["content"]}
        for msg in interview.conversation_history
    ])
    
    next_question = await llm_service.generate_response(
        messages,
        temperature=0.7,
        max_tokens=300
    )
    
    # Add AI question
    interview.current_question_index += 1
    interview.conversation_history.append({
        "role": "assistant",
        "content": next_question,
        "timestamp": datetime.utcnow().isoformat(),
        "question_number": interview.current_question_index
    })
    
    attributes.flag_modified(interview, "conversation_history")
    
    # Check if should end
    if interview.current_question_index >= 10:
        interview.status = InterviewStatus.COMPLETED
        interview.completed_at = datetime.utcnow()
        
        if interview.started_at:
            duration = (interview.completed_at - interview.started_at).total_seconds()
            interview.duration_seconds = int(duration)
        
        # Update candidate status
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.id == interview.candidate_id)
        )
        candidate = candidate_result.scalar_one()
        candidate.status = CandidateStatus.INTERVIEW_COMPLETED
        candidate.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(interview)
    
    return {
        "success": True,
        "next_question": next_question,
        "question_number": interview.current_question_index,
        "is_complete": interview.status == InterviewStatus.COMPLETED
    }


@router.post("/{interview_id}/complete")
async def complete_interview(
    interview_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually complete an interview
    """
    logger.info("interview_complete_request", interview_id=interview_id)
    
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found"
        )
    
    if interview.status == InterviewStatus.COMPLETED:
        return {"success": True, "message": "Interview already completed"}
    
    # Mark as completed
    interview.status = InterviewStatus.COMPLETED
    interview.completed_at = datetime.utcnow()
    
    if interview.started_at:
        duration = (interview.completed_at - interview.started_at).total_seconds()
        interview.duration_seconds = int(duration)
    
    # Update candidate status
    candidate_result = await db.execute(
        select(Candidate).where(Candidate.id == interview.candidate_id)
    )
    candidate = candidate_result.scalar_one_or_none()
    if candidate:
        candidate.status = CandidateStatus.INTERVIEW_COMPLETED
        candidate.updated_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info("interview_completed_manually", interview_id=interview_id)
    
    return {"success": True, "message": "Interview completed successfully"}


@router.get("/{interview_id}", response_model=InterviewDetail)
async def get_interview(
    interview_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get interview details including full conversation history
    """
    logger.info("interview_get_request", interview_id=interview_id)
    
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found"
        )
    
    # Get related data
    job_result = await db.execute(select(Job).where(Job.id == interview.job_id))
    job = job_result.scalar_one()
    
    response = InterviewDetail.model_validate(interview)
    response.job_title = job.title
    response.candidate_name = interview.candidate_context.get('name')
    
    logger.info("interview_get_response", interview_id=interview_id)
    return response


@router.get("/", response_model=List[InterviewResponse])
async def list_interviews(
    job_id: Optional[int] = Query(None, description="Filter by job"),
    candidate_id: Optional[int] = Query(None, description="Filter by candidate"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List all interviews with optional filters
    """
    logger.info("interview_list_request", job_id=job_id, candidate_id=candidate_id)
    
    # Build query
    query = select(Interview)
    
    if job_id:
        query = query.where(Interview.job_id == job_id)
    
    if candidate_id:
        query = query.where(Interview.candidate_id == candidate_id)
    
    if status:
        try:
            interview_status = InterviewStatus(status)
            query = query.where(Interview.status == interview_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    query = query.order_by(Interview.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    interviews = result.scalars().all()
    
    # Build responses with related data
    responses = []
    for interview in interviews:
        # Get job title
        job_result = await db.execute(select(Job.title).where(Job.id == interview.job_id))
        job_title = job_result.scalar()
        
        response = InterviewResponse.model_validate(interview)
        response.job_title = job_title
        response.candidate_name = interview.candidate_context.get('name')
        responses.append(response)
    
    logger.info("interview_list_response", count=len(responses))
    return responses


@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview(
    interview_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an interview
    
    - **interview_id**: ID of the interview to delete
    """
    logger.info("interview_delete_request", interview_id=interview_id)
    
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found"
        )
    
    candidate_id = interview.candidate_id
    
    # Delete interview
    await db.delete(interview)
    await db.commit()
    
    # Update candidate status if they have no other interviews
    candidate_result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = candidate_result.scalar_one_or_none()
    
    if candidate:
        remaining_interviews = await db.execute(
            select(func.count(Interview.id))
            .where(Interview.candidate_id == candidate_id)
        )
        count = remaining_interviews.scalar()
        
        if count == 0 and candidate.status == CandidateStatus.INTERVIEW_SCHEDULED:
            candidate.status = CandidateStatus.APPLIED
            candidate.updated_at = datetime.utcnow()
            await db.commit()
    
    logger.info("interview_deleted", interview_id=interview_id)
    return None


@router.get("/{interview_id}/assessment", response_model=AssessmentProgress)
async def get_interview_assessment(
    interview_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get real-time assessment progress for an ongoing interview
    """
    logger.info("interview_assessment_request", interview_id=interview_id)
    
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found"
        )
    
    # Get current dimension scores
    scores_result = await db.execute(
        select(DimensionScore).where(DimensionScore.interview_id == interview_id)
    )
    dimension_scores = scores_result.scalars().all()
    
    # Count questions
    questions_completed = sum(1 for msg in interview.conversation_history if msg["role"] == "user")
    
    return AssessmentProgress(
        interview_id=interview_id,
        questions_completed=questions_completed,
        total_questions=10,
        current_dimension_scores=[
            DimensionScoreResponse(
                id=ds.id,
                interview_id=ds.interview_id,
                dimension_name=ds.dimension_name,
                score=ds.score,
                max_score=ds.max_score,
                reasoning=ds.reasoning or "",
                evidence=ds.evidence or [],
                created_at=ds.created_at
            ) for ds in dimension_scores
        ],
        recent_evidence=[],  # Could be enhanced to show recent evidence
        estimated_completion=None
    )


@router.post("/{interview_id}/report", response_model=ComprehensiveReport)
async def generate_interview_report(
    interview_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate comprehensive evaluation report for a completed interview
    
    This endpoint performs multi-dimensional assessment and generates:
    - Overall recommendation (Strong Hire / Hire / No Hire / Strong No Hire)
    - Dimension scores with evidence
    - Key strengths and areas of concern
    - Notable quotes
    - Suggested follow-up questions
    - Full transcript
    """
    logger.info("interview_report_request", interview_id=interview_id)
    
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found"
        )
    
    # Generate comprehensive report
    assessment_service = AssessmentService(db, llm_service)
    try:
        report = await assessment_service.generate_comprehensive_report(interview_id)
        logger.info("interview_report_generated", 
                   interview_id=interview_id,
                   recommendation=report.recommendation,
                   overall_score=report.overall_score)
        return report
    except Exception as e:
        logger.error(f"Failed to generate report: {e}", interview_id=interview_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )
