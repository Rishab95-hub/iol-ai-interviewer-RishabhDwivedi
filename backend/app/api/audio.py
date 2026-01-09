"""
Audio API endpoints for Speech-to-Text and Text-to-Speech
Handles audio processing for voice interviews
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import io

from app.core.logging import get_logger
from app.services.speech_to_text_v2 import get_stt_service
from app.services.text_to_speech_v2 import get_tts_service, EDGE_TTS_AVAILABLE, GTTS_AVAILABLE, PYTTSX3_AVAILABLE

logger = get_logger(__name__)
router = APIRouter()


class TranscriptionResponse(BaseModel):
    """Response for transcription"""
    text: str
    duration: Optional[float] = None
    language: str = "en"


class TTSRequest(BaseModel):
    """Request for text-to-speech"""
    text: str
    speed: float = 1.0
    format: str = "mp3"  # mp3 or wav


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = "en"
):
    """
    Transcribe audio file to text using Hugging Face Whisper
    
    - **audio**: Audio file (WAV, MP3, M4A, etc.)
    - **language**: Language code (en, es, fr, etc.)
    
    Returns transcribed text
    """
    logger.info("transcribe_request", filename=audio.filename, language=language)
    
    # Validate file type
    if not audio.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an audio file"
        )
    
    try:
        # Read audio data
        audio_data = await audio.read()
        
        # Get STT service
        stt_service = get_stt_service(model_size="base")
        
        # Transcribe (run in thread pool since it's CPU intensive)
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            stt_service.transcribe_audio,
            audio_data,
            language,
            False
        )
        
        return TranscriptionResponse(
            text=result["text"],
            language=language
        )
        
    except Exception as e:
        logger.error("transcription_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}"
        )


@router.post("/synthesize", response_class=StreamingResponse)
async def synthesize_speech(request: TTSRequest):
    """
    Convert text to speech using Hugging Face TTS models
    
    - **text**: Text to convert to speech
    - **speed**: Speech speed (0.5-2.0, default 1.0)
    - **format**: Audio format (mp3 or wav)
    
    Returns audio file stream
    """
    logger.info("tts_request", text_length=len(request.text), format=request.format)
    
    if not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text cannot be empty"
        )
    
    if not 0.5 <= request.speed <= 2.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Speed must be between 0.5 and 2.0"
        )
    
    try:
        # Get TTS service
        tts_service = get_tts_service()
        
        # Synthesize speech
        audio_bytes = await tts_service.synthesize_speech(
            text=request.text,
            output_format=request.format,
            speed=request.speed
        )
        
        # Return as streaming response
        audio_stream = io.BytesIO(audio_bytes)
        
        media_type = f"audio/{request.format}"
        
        return StreamingResponse(
            audio_stream,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{request.format}"
            }
        )
        
    except Exception as e:
        logger.error("tts_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech synthesis failed: {str(e)}"
        )


@router.get("/health")
async def audio_health_check():
    """Check if audio services are available"""
    try:
        stt_service = get_stt_service()
        tts_service = get_tts_service()
        
        # Get available TTS engines
        tts_engines = tts_service.get_available_engines()
        tts_status = "available" if any(tts_engines.values()) else "unavailable"
        
        return {
            "status": "healthy",
            "services": {
                "speech_to_text": "available",
                "text_to_speech": tts_status,
                "tts_engines": tts_engines,
                "stt_model": stt_service.model_size
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e)
        }
