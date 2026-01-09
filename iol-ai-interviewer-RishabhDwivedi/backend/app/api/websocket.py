"""
WebSocket endpoint for real-time interviews
Handles live candidate-AI interaction with streaming responses
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Dict, Set
import json
import asyncio

from app.core.database import get_db
from app.core.logging import get_logger
from app.models import Interview, InterviewStatus
from app.services.llm_service import LLMService

logger = get_logger(__name__)
router = APIRouter()

# Active WebSocket connections
active_connections: Dict[int, Set[WebSocket]] = {}


class ConnectionManager:
    """Manage WebSocket connections for interviews"""
    
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
    
    async def connect(self, interview_id: int, websocket: WebSocket):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        self.active_connections[interview_id] = websocket
        logger.info("websocket_connected", interview_id=interview_id)
    
    def disconnect(self, interview_id: int):
        """Remove WebSocket connection"""
        if interview_id in self.active_connections:
            del self.active_connections[interview_id]
            logger.info("websocket_disconnected", interview_id=interview_id)
    
    async def send_message(self, interview_id: int, message: dict):
        """Send message to specific interview WebSocket"""
        if interview_id in self.active_connections:
            await self.active_connections[interview_id].send_json(message)
    
    async def send_stream_chunk(self, interview_id: int, chunk: str):
        """Send streaming text chunk"""
        if interview_id in self.active_connections:
            await self.active_connections[interview_id].send_json({
                "type": "stream_chunk",
                "content": chunk
            })
    
    async def send_stream_complete(self, interview_id: int, full_response: str):
        """Signal streaming complete"""
        if interview_id in self.active_connections:
            await self.active_connections[interview_id].send_json({
                "type": "stream_complete",
                "content": full_response
            })


manager = ConnectionManager()


@router.websocket("/ws/interview/{interview_id}")
async def interview_websocket(
    websocket: WebSocket,
    interview_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time interview interaction
    
    Message Format (Candidate -> Server):
    {
        "type": "candidate_message",
        "content": "My answer is..."
    }
    
    Message Format (Server -> Candidate):
    {
        "type": "ai_question",
        "content": "Can you explain...",
        "question_number": 3,
        "total_questions": 10
    }
    
    Streaming Format:
    {
        "type": "stream_chunk",
        "content": "partial text..."
    }
    """
    
    # Verify interview exists
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    
    if not interview:
        await websocket.close(code=1008, reason="Interview not found")
        return
    
    # Connect WebSocket
    await manager.connect(interview_id, websocket)
    
    try:
        # Send initial greeting
        await manager.send_message(interview_id, {
            "type": "system",
            "content": "Connected to interview session. Type 'ready' to begin."
        })
        
        # Initialize LLM service
        llm_service = LLMService()
        
        while True:
            # Receive message from candidate
            data = await websocket.receive_json()
            
            if data.get("type") == "candidate_message":
                content = data.get("content", "").strip()
                
                if not content:
                    continue
                
                # Handle start command
                if content.lower() == "ready" and interview.status == InterviewStatus.PENDING:
                    # Start interview
                    interview.status = InterviewStatus.IN_PROGRESS
                    interview.started_at = datetime.utcnow()
                    await db.commit()
                    
                    # Get first question
                    first_question = await llm_service.get_interview_question(
                        interview=interview,
                        question_number=0
                    )
                    
                    # Add to conversation history
                    if interview.conversation_history is None:
                        interview.conversation_history = []
                    
                    interview.conversation_history.append({
                        "role": "assistant",
                        "content": first_question,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    interview.current_question_index = 1
                    await db.commit()
                    
                    # Send first question
                    await manager.send_message(interview_id, {
                        "type": "ai_question",
                        "content": first_question,
                        "question_number": 1,
                        "total_questions": 10
                    })
                    
                    continue
                
                # Check if interview is in progress
                if interview.status != InterviewStatus.IN_PROGRESS:
                    await manager.send_message(interview_id, {
                        "type": "error",
                        "content": "Interview is not in progress"
                    })
                    continue
                
                # Add candidate response to history
                interview.conversation_history.append({
                    "role": "user",
                    "content": content,
                    "timestamp": datetime.utcnow().isoformat()
                })
                await db.commit()
                
                # Generate next question with streaming
                await manager.send_message(interview_id, {
                    "type": "system",
                    "content": "AI is thinking..."
                })
                
                # Stream AI response
                full_response = ""
                async for chunk in llm_service.stream_interview_response(
                    interview=interview,
                    candidate_response=content
                ):
                    full_response += chunk
                    await manager.send_stream_chunk(interview_id, chunk)
                    await asyncio.sleep(0.01)  # Small delay for smooth streaming
                
                # Signal streaming complete
                await manager.send_stream_complete(interview_id, full_response)
                
                # Add AI response to history
                interview.conversation_history.append({
                    "role": "assistant",
                    "content": full_response,
                    "timestamp": datetime.utcnow().isoformat()
                })
                interview.current_question_index += 1
                await db.commit()
                
                # Check if interview should end
                if interview.current_question_index >= 10:
                    # Complete interview
                    interview.status = InterviewStatus.COMPLETED
                    interview.completed_at = datetime.utcnow()
                    
                    if interview.started_at:
                        duration = (interview.completed_at - interview.started_at).total_seconds()
                        interview.duration_seconds = int(duration)
                    
                    await db.commit()
                    
                    await manager.send_message(interview_id, {
                        "type": "system",
                        "content": "Interview completed! Thank you for your time."
                    })
                    
                    # Close connection
                    await websocket.close(code=1000, reason="Interview completed")
                    break
    
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", interview_id=interview_id)
        manager.disconnect(interview_id)
    
    except Exception as e:
        logger.error("websocket_error", interview_id=interview_id, error=str(e))
        manager.disconnect(interview_id)
        try:
            await websocket.close(code=1011, reason=f"Server error: {str(e)}")
        except:
            pass
