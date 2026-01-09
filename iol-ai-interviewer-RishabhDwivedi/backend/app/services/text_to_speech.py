"""
Text-to-Speech Service using Hugging Face models
Converts AI responses to speech for interview audio
"""
from typing import Optional
import torch
from TTS.api import TTS
import numpy as np
import io
from pydub import AudioSegment

from app.core.logging import get_logger

logger = get_logger(__name__)


class TextToSpeechService:
    """
    Text-to-Speech service using Coqui TTS (Hugging Face compatible)
    """
    
    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"):
        """
        Initialize TTS model
        
        Popular models:
        - tts_models/en/ljspeech/tacotron2-DDC (Fast, good quality)
        - tts_models/en/ljspeech/glow-tts (Faster)
        - tts_models/en/vctk/vits (Multi-speaker)
        - tts_models/multilingual/multi-dataset/your_tts (Multilingual)
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(
            "tts_initializing",
            model=model_name,
            device=self.device
        )
        
        try:
            # Initialize TTS
            self.tts = TTS(model_name=model_name).to(self.device)
            
            logger.info("tts_initialized_successfully")
            
        except Exception as e:
            logger.error("tts_initialization_failed", error=str(e))
            # Fallback to simple TTS
            logger.warning("falling_back_to_simple_tts")
            self.tts = None
    
    async def synthesize_speech(
        self,
        text: str,
        output_format: str = "wav",
        speed: float = 1.0
    ) -> bytes:
        """
        Convert text to speech audio
        
        Args:
            text: Text to convert
            output_format: Output format (wav, mp3)
            speed: Speech speed multiplier (0.5-2.0)
            
        Returns:
            Audio bytes
        """
        try:
            if self.tts is None:
                # Fallback to simple TTS
                return await self._simple_tts(text, output_format)
            
            # Generate speech
            wav = self.tts.tts(text=text, speed=speed)
            
            # Convert to bytes
            audio_bytes = io.BytesIO()
            
            # Convert numpy array to audio file
            sample_rate = self.tts.synthesizer.output_sample_rate
            audio_segment = AudioSegment(
                wav.tobytes(),
                frame_rate=sample_rate,
                sample_width=2,  # 16-bit
                channels=1
            )
            
            # Export in requested format
            audio_segment.export(audio_bytes, format=output_format)
            
            audio_bytes.seek(0)
            result = audio_bytes.read()
            
            logger.info(
                "speech_synthesized",
                text_length=len(text),
                audio_size=len(result),
                format=output_format
            )
            
            return result
            
        except Exception as e:
            logger.error("speech_synthesis_failed", error=str(e))
            # Try fallback
            return await self._simple_tts(text, output_format)
    
    async def _simple_tts(self, text: str, output_format: str = "mp3") -> bytes:
        """
        Fallback simple TTS using gTTS (Google Text-to-Speech)
        Requires internet connection but very simple
        """
        try:
            from gtts import gTTS
            
            tts = gTTS(text=text, lang='en', slow=False)
            
            audio_bytes = io.BytesIO()
            tts.write_to_fp(audio_bytes)
            audio_bytes.seek(0)
            
            # Convert to requested format if needed
            if output_format != "mp3":
                audio = AudioSegment.from_mp3(audio_bytes)
                output_bytes = io.BytesIO()
                audio.export(output_bytes, format=output_format)
                output_bytes.seek(0)
                return output_bytes.read()
            
            return audio_bytes.read()
            
        except ImportError:
            logger.error("gtts_not_installed")
            raise Exception("TTS not available. Install with: pip install gTTS")
        except Exception as e:
            logger.error("simple_tts_failed", error=str(e))
            raise
    
    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        speed: float = 1.0
    ):
        """
        Convert text to speech and save to file
        
        Args:
            text: Text to convert
            output_path: Path to save audio file
            speed: Speech speed
        """
        try:
            audio_bytes = await self.synthesize_speech(text, output_format="wav", speed=speed)
            
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)
            
            logger.info("speech_saved_to_file", path=output_path, size=len(audio_bytes))
            
        except Exception as e:
            logger.error("save_speech_failed", error=str(e), path=output_path)
            raise


# Singleton instance
_tts_service: Optional[TextToSpeechService] = None


def get_tts_service(model_name: Optional[str] = None) -> TextToSpeechService:
    """Get or create TTS service instance"""
    global _tts_service
    
    if _tts_service is None:
        if model_name:
            _tts_service = TextToSpeechService(model_name=model_name)
        else:
            _tts_service = TextToSpeechService()
    
    return _tts_service
