"""
Text-to-Speech service using multiple TTS engines.
Primary: Edge TTS (Microsoft Edge) - high quality, free
Fallback: gTTS (Google) - requires internet
Fallback: pyttsx3 (offline) - lower quality but always available
"""

import asyncio
import os
import tempfile
from typing import Optional
from pydub import AudioSegment
import logging

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

logger = logging.getLogger(__name__)


class TextToSpeechService:
    """Text-to-Speech service with multiple engine support."""
    
    def __init__(self, preferred_engine: str = "edge"):
        """
        Initialize TTS service.
        
        Args:
            preferred_engine: "edge", "gtts", or "pyttsx3"
        """
        self.preferred_engine = preferred_engine
        self.pyttsx3_engine = None
        
        if preferred_engine == "pyttsx3" and PYTTSX3_AVAILABLE:
            self.pyttsx3_engine = pyttsx3.init()
            
        logger.info(f"TTS Service initialized. Engines available - Edge: {EDGE_TTS_AVAILABLE}, gTTS: {GTTS_AVAILABLE}, pyttsx3: {PYTTSX3_AVAILABLE}")
    
    async def synthesize_speech(
        self,
        text: str,
        output_format: str = "mp3",
        speed: float = 1.0,
        voice: Optional[str] = None
    ) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to convert to speech
            output_format: "mp3" or "wav"
            speed: Speech speed (0.5 to 2.0)
            voice: Voice name (engine-specific)
            
        Returns:
            Audio data as bytes
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        if speed < 0.5 or speed > 2.0:
            raise ValueError("Speed must be between 0.5 and 2.0")
        
        # Try Edge TTS first (best quality)
        if EDGE_TTS_AVAILABLE:
            try:
                return await self._edge_tts(text, output_format, speed, voice)
            except Exception as e:
                logger.warning(f"Edge TTS failed: {e}, falling back to gTTS")
        
        # Try gTTS (good quality, requires internet)
        if GTTS_AVAILABLE:
            try:
                return await self._gtts(text, output_format, speed)
            except Exception as e:
                logger.warning(f"gTTS failed: {e}, falling back to pyttsx3")
        
        # Try pyttsx3 (offline, lower quality)
        if PYTTSX3_AVAILABLE:
            try:
                return await self._pyttsx3(text, output_format, speed)
            except Exception as e:
                logger.error(f"pyttsx3 failed: {e}")
                raise RuntimeError("All TTS engines failed")
        
        raise RuntimeError("No TTS engine available")
    
    async def _edge_tts(
        self,
        text: str,
        output_format: str,
        speed: float,
        voice: Optional[str]
    ) -> bytes:
        """Synthesize using Microsoft Edge TTS."""
        if not voice:
            voice = "en-US-AriaNeural"  # Default female voice
        
        # Edge TTS rate: -50% to +100%
        rate_percent = int((speed - 1.0) * 100)
        rate = f"{rate_percent:+d}%"
        
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp_path = tmp.name
        
        try:
            # Synthesize
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(tmp_path)
            
            # Read audio
            if output_format == "wav":
                audio = AudioSegment.from_mp3(tmp_path)
                wav_path = tmp_path.replace(".mp3", ".wav")
                audio.export(wav_path, format="wav")
                
                with open(wav_path, "rb") as f:
                    audio_data = f.read()
                
                os.unlink(wav_path)
            else:
                with open(tmp_path, "rb") as f:
                    audio_data = f.read()
            
            return audio_data
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    async def _gtts(self, text: str, output_format: str, speed: float) -> bytes:
        """Synthesize using Google TTS."""
        # gTTS doesn't support speed adjustment directly
        # We'll adjust audio speed after generation
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp_path = tmp.name
        
        try:
            # Generate speech
            tts = gTTS(text=text, lang='en', slow=(speed < 0.8))
            tts.save(tmp_path)
            
            # Load audio
            audio = AudioSegment.from_mp3(tmp_path)
            
            # Adjust speed if needed
            if speed != 1.0:
                # Change speed without changing pitch
                sound_with_altered_frame_rate = audio._spawn(
                    audio.raw_data,
                    overrides={"frame_rate": int(audio.frame_rate * speed)}
                )
                audio = sound_with_altered_frame_rate.set_frame_rate(audio.frame_rate)
            
            # Convert format
            if output_format == "wav":
                output_path = tmp_path.replace(".mp3", ".wav")
                audio.export(output_path, format="wav")
            else:
                output_path = tmp_path
                audio.export(output_path, format="mp3")
            
            # Read audio data
            with open(output_path, "rb") as f:
                audio_data = f.read()
            
            return audio_data
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            output_path = tmp_path.replace(".mp3", ".wav")
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    async def _pyttsx3(self, text: str, output_format: str, speed: float) -> bytes:
        """Synthesize using pyttsx3 (offline)."""
        if not self.pyttsx3_engine:
            self.pyttsx3_engine = pyttsx3.init()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = tmp.name
        
        try:
            # Set properties
            rate = self.pyttsx3_engine.getProperty('rate')
            self.pyttsx3_engine.setProperty('rate', rate * speed)
            
            # Save to file
            self.pyttsx3_engine.save_to_file(text, tmp_path)
            self.pyttsx3_engine.runAndWait()
            
            # Load and convert if needed
            audio = AudioSegment.from_wav(tmp_path)
            
            if output_format == "mp3":
                output_path = tmp_path.replace(".wav", ".mp3")
                audio.export(output_path, format="mp3")
            else:
                output_path = tmp_path
            
            # Read audio data
            with open(output_path, "rb") as f:
                audio_data = f.read()
            
            return audio_data
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            output_path = tmp_path.replace(".wav", ".mp3")
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        speed: float = 1.0,
        voice: Optional[str] = None
    ) -> str:
        """
        Synthesize speech and save to file.
        
        Args:
            text: Text to convert
            output_path: Path to save audio file
            speed: Speech speed
            voice: Voice name
            
        Returns:
            Path to saved file
        """
        # Determine format from extension
        output_format = "mp3" if output_path.endswith(".mp3") else "wav"
        
        # Synthesize
        audio_data = await self.synthesize_speech(text, output_format, speed, voice)
        
        # Save to file
        with open(output_path, "wb") as f:
            f.write(audio_data)
        
        return output_path
    
    def get_available_engines(self) -> dict:
        """Get status of available TTS engines."""
        return {
            "edge_tts": EDGE_TTS_AVAILABLE,
            "gtts": GTTS_AVAILABLE,
            "pyttsx3": PYTTSX3_AVAILABLE
        }


# Singleton instance
_tts_service: Optional[TextToSpeechService] = None


def get_tts_service(preferred_engine: str = "edge") -> TextToSpeechService:
    """Get or create TTS service singleton."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TextToSpeechService(preferred_engine)
    return _tts_service
