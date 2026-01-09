"""
Speech-to-Text Service using Hugging Face Whisper
Handles audio transcription for interview recordings
"""
from typing import Optional, BinaryIO
import torch
from transformers import pipeline
import numpy as np
import soundfile as sf
from io import BytesIO
import tempfile
import os

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class SpeechToTextService:
    """
    Speech-to-Text service using Hugging Face Whisper model
    """
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize Whisper model
        
        Args:
            model_size: Model size (tiny, base, small, medium, large-v3)
                       - tiny: Fastest, least accurate
                       - base: Good balance (default)
                       - small: Better accuracy
                       - medium/large: Best accuracy, slower
        """
        self.model_size = model_size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(
            "stt_initializing",
            model=f"openai/whisper-{model_size}",
            device=self.device
        )
        
        try:
            # Initialize Whisper pipeline
            self.pipe = pipeline(
                "automatic-speech-recognition",
                model=f"openai/whisper-{model_size}",
                device=self.device,
                chunk_length_s=30,  # Process 30-second chunks
                return_timestamps=True
            )
            
            logger.info("stt_initialized_successfully")
            
        except Exception as e:
            logger.error("stt_initialization_failed", error=str(e))
            raise
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        language: str = "en",
        return_timestamps: bool = False
    ) -> dict:
        """
        Transcribe audio bytes to text
        
        Args:
            audio_data: Audio file bytes (WAV, MP3, etc.)
            language: Language code (en, es, fr, etc.)
            return_timestamps: Whether to include word timestamps
            
        Returns:
            {
                "text": "transcribed text",
                "chunks": [{"timestamp": [0.0, 2.5], "text": "hello"}] (if timestamps)
            }
        """
        try:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            # Transcribe
            result = self.pipe(
                temp_path,
                generate_kwargs={
                    "language": language,
                    "task": "transcribe"
                },
                return_timestamps=return_timestamps
            )
            
            # Clean up
            os.unlink(temp_path)
            
            logger.info(
                "audio_transcribed",
                text_length=len(result["text"]),
                has_timestamps=return_timestamps
            )
            
            return result
            
        except Exception as e:
            logger.error("transcription_failed", error=str(e))
            raise
    
    async def transcribe_stream(
        self,
        audio_stream: BinaryIO,
        sample_rate: int = 16000
    ) -> str:
        """
        Transcribe audio from stream (for real-time processing)
        
        Args:
            audio_stream: Audio stream
            sample_rate: Sample rate in Hz
            
        Returns:
            Transcribed text
        """
        try:
            # Read audio data
            audio_data, sr = sf.read(audio_stream)
            
            # Resample if needed
            if sr != sample_rate:
                import librosa
                audio_data = librosa.resample(
                    audio_data,
                    orig_sr=sr,
                    target_sr=sample_rate
                )
            
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            
            # Transcribe
            result = self.pipe(
                {"sampling_rate": sample_rate, "raw": audio_data},
                generate_kwargs={"language": "en"}
            )
            
            return result["text"]
            
        except Exception as e:
            logger.error("stream_transcription_failed", error=str(e))
            raise
    
    async def transcribe_file_path(
        self,
        file_path: str,
        language: str = "en"
    ) -> str:
        """
        Transcribe audio file from path
        
        Args:
            file_path: Path to audio file
            language: Language code
            
        Returns:
            Transcribed text
        """
        try:
            result = self.pipe(
                file_path,
                generate_kwargs={
                    "language": language,
                    "task": "transcribe"
                }
            )
            
            logger.info(
                "file_transcribed",
                file=file_path,
                text_length=len(result["text"])
            )
            
            return result["text"]
            
        except Exception as e:
            logger.error("file_transcription_failed", error=str(e), file=file_path)
            raise


# Singleton instance
_stt_service: Optional[SpeechToTextService] = None


def get_stt_service(model_size: str = "base") -> SpeechToTextService:
    """Get or create STT service instance"""
    global _stt_service
    
    if _stt_service is None:
        _stt_service = SpeechToTextService(model_size=model_size)
    
    return _stt_service
