"""
Speech-to-Text service using OpenAI Whisper model.
Optimized version with audio preprocessing and prompt engineering.
"""

import os
import tempfile
from typing import Optional, List
import logging
import soundfile as sf
import numpy as np
from pydub import AudioSegment
from pydub.effects import normalize
import glob
from scipy import signal

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

logger = logging.getLogger(__name__)

# Find and add ffmpeg to PATH for pydub
ffmpeg_pattern = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "ffmpeg-*", "bin")
ffmpeg_dirs = glob.glob(ffmpeg_pattern)
if ffmpeg_dirs:
    ffmpeg_dir = ffmpeg_dirs[0]
    # Add to PATH so pydub can find ffmpeg/ffprobe
    current_path = os.environ.get("PATH", "")
    if ffmpeg_dir not in current_path:
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + current_path
        logger.info(f"Added ffmpeg to PATH: {ffmpeg_dir}")
    
    # Also set directly on AudioSegment
    AudioSegment.converter = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    AudioSegment.ffprobe = os.path.join(ffmpeg_dir, "ffprobe.exe")


class SpeechToTextService:
    """Speech-to-Text service using OpenAI Whisper."""
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize STT service.
        
        Args:
            model_size: Whisper model size - "tiny", "base", "small", "medium", "large"
                       Larger models are more accurate but slower
        """
        if not WHISPER_AVAILABLE:
            raise ImportError("OpenAI Whisper not installed. Run: pip install openai-whisper")
        
        self.model_size = model_size
        self.model = None
        self.device = "cpu"  # Whisper uses CPU by default
        logger.info(f"STT Service initialized with model size: {model_size}")
    
    def _load_model(self):
        """Lazy load Whisper model."""
        if self.model is None:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.model = whisper.load_model(self.model_size)
            logger.info("Whisper model loaded successfully")
    
    def transcribe_audio(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        return_timestamps: bool = False
    ) -> dict:
        """
        Transcribe audio data with advanced preprocessing and prompt engineering.
        
        Args:
            audio_data: Audio file bytes
            language: Language code (e.g., "en", "es") or None for auto-detect
            return_timestamps: Whether to return timestamps
            
        Returns:
            dict with "text", "language", and optionally "segments"
        """
        self._load_model()
        
        # Create temp files
        import uuid
        from pydub import AudioSegment
        
        temp_id = uuid.uuid4().hex
        input_path = os.path.join(tempfile.gettempdir(), f"whisper_input_{temp_id}")
        output_path = os.path.join(tempfile.gettempdir(), f"whisper_output_{temp_id}.wav")
        
        logger.info(f"Audio data size: {len(audio_data)} bytes")
        
        try:
            # Write input audio to file
            with open(input_path, 'wb') as f:
                f.write(audio_data)
            
            logger.info(f"Preprocessing audio")
            # Load audio with pydub
            audio = AudioSegment.from_file(input_path)
            
            # 1. Convert to mono
            audio = audio.set_channels(1)
            
            # 2. Normalize audio levels
            audio = normalize(audio)
            
            # 3. Remove silence and noise (apply high-pass filter via export)
            audio = audio.set_frame_rate(16000)  # Whisper expects 16kHz
            
            # Export preprocessed audio
            audio.export(output_path, format="wav")
            logger.info(f"Preprocessed WAV created: {output_path}")
            
            # Load preprocessed audio
            audio_array, sample_rate = sf.read(output_path)
            
            # 4. Apply noise reduction using spectral gating
            audio_array = self._reduce_noise(audio_array, sample_rate)
            
            # Ensure float32 and normalize to [-1, 1]
            audio_array = audio_array.astype(np.float32)
            max_val = np.abs(audio_array).max()
            if max_val > 0:
                audio_array = audio_array / max_val
            
            logger.info(f"Audio preprocessed: shape={audio_array.shape}, sample_rate={sample_rate}, max={audio_array.max():.3f}")
            
            # 5. Build prompt for better context
            initial_prompt = self._build_transcription_prompt(language)
            
            # 6. Transcribe with optimized parameters
            options = {
                "initial_prompt": initial_prompt,
                "task": "transcribe",
                "temperature": 0.0,  # More deterministic
                "no_speech_threshold": 0.4,  # Lower threshold for detecting speech
                "condition_on_previous_text": True,  # Better context
                "compression_ratio_threshold": 2.4,  # Detect hallucinations
                "logprob_threshold": -1.0,  # Quality threshold
            }
            
            if language:
                options["language"] = language
            
            logger.info(f"Starting transcription with prompt: {initial_prompt[:100]}...")
            result = self.model.transcribe(audio_array, **options)
            
            transcribed_text = result["text"].strip()
            logger.info(f"Transcription completed: {len(transcribed_text)} chars - TEXT: '{transcribed_text}'")
            
            return {
                "text": transcribed_text,
                "language": result.get("language", "unknown"),
                "segments": result.get("segments", [])
            }
        
        finally:
            # Clean up temp files
            for path in [input_path, output_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except:
                        pass
    
    def _reduce_noise(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Apply spectral gating for noise reduction.
        Simple implementation using high-pass filtering.
        """
        try:
            # High-pass filter to remove low-frequency noise
            nyquist = sample_rate / 2
            cutoff = 80  # Hz - remove very low frequencies
            normalized_cutoff = cutoff / nyquist
            
            # Design butterworth high-pass filter
            b, a = signal.butter(4, normalized_cutoff, btype='high')
            filtered = signal.filtfilt(b, a, audio)
            
            return filtered.astype(np.float32)
        except Exception as e:
            logger.warning(f"Noise reduction failed: {e}, using original audio")
            return audio
    
    def _build_transcription_prompt(self, language: Optional[str] = None) -> str:
        """
        Build an initial prompt to guide Whisper transcription.
        This helps Whisper understand the context and reduces errors.
        """
        base_prompt = (
            "This is a professional job interview conversation. "
            "The speaker is answering technical interview questions about "
            "backend development, software engineering, Python, Java, Node.js, "
            "databases, APIs, system design, and cloud technologies. "
            "The speech is clear and professional. "
            "Transcribe accurately with proper punctuation and capitalization."
        )
        
        if language == "en":
            return base_prompt
        else:
            return base_prompt
    
    def transcribe_file_path(
        self,
        file_path: str,
        language: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio from file path.
        
        Args:
            file_path: Path to audio file
            language: Language code or None for auto-detect
            
        Returns:
            dict with "text", "language", and optionally "segments"
        """
        self._load_model()
        
        options = {}
        if language:
            options["language"] = language
        
        result = self.model.transcribe(file_path, **options)
        
        return {
            "text": result["text"].strip(),
            "language": result.get("language", "unknown"),
            "segments": result.get("segments", []),
            "duration": self._get_audio_duration(file_path)
        }
    
    def _get_audio_duration(self, file_path: str) -> float:
        """Get audio file duration in seconds."""
        try:
            audio_data, sample_rate = sf.read(file_path)
            return len(audio_data) / sample_rate
        except Exception as e:
            logger.warning(f"Could not get audio duration: {e}")
            return 0.0
    
    def transcribe_stream(
        self,
        audio_stream: bytes,
        sample_rate: int = 16000,
        language: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio from byte stream.
        
        Args:
            audio_stream: Raw audio bytes
            sample_rate: Audio sample rate
            language: Language code or None
            
        Returns:
            dict with "text", "language"
        """
        # Save stream to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = tmp.name
            tmp.write(audio_stream)
        
        try:
            return self.transcribe_file_path(tmp_path, language)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_size": self.model_size,
            "loaded": self.model is not None,
            "available": WHISPER_AVAILABLE
        }


# Singleton instance
_stt_service: Optional[SpeechToTextService] = None


def get_stt_service(model_size: str = "small") -> SpeechToTextService:
    """Get or create STT service singleton. Using 'small' model for better accuracy."""
    global _stt_service
    if _stt_service is None:
        _stt_service = SpeechToTextService(model_size)
    return _stt_service
