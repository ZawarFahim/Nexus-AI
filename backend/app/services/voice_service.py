import os
import io
import wave
import logging
from typing import AsyncGenerator
from faster_whisper import WhisperModel

# Attempt to import piper. Depending on how it's installed, it might be piper or piper_tts.
try:
    from piper import PiperVoice
except ImportError:
    PiperVoice = None

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self):
        self.whisper_model = None
        self.piper_voice = None
        
        # We use 'tiny.en' or 'base.en' for rapid transcription
        self.whisper_model_size = "tiny.en"
        
        # Path where Piper models should be stored
        self.piper_model_path = os.path.join(os.getcwd(), "models", "en_US-lessac-medium.onnx")
        self.piper_config_path = self.piper_model_path + ".json"

    def _ensure_whisper(self):
        if not self.whisper_model:
            logger.info(f"Loading Faster Whisper model: {self.whisper_model_size}...")
            # Compute type int8 for speed and low memory on CPU
            self.whisper_model = WhisperModel(self.whisper_model_size, device="cpu", compute_type="int8")
            logger.info("Faster Whisper loaded.")

    def _ensure_piper(self):
        if not self.piper_voice:
            if not PiperVoice:
                logger.error("PiperVoice module not found. Is piper-tts installed?")
                return False
                
            if not os.path.exists(self.piper_model_path):
                logger.error(f"Piper model not found at {self.piper_model_path}. Please download it.")
                # In production, we would automatically wget the model here from huggingface
                return False
                
            logger.info(f"Loading Piper TTS model: {self.piper_model_path}...")
            self.piper_voice = PiperVoice.load(self.piper_model_path, config_path=self.piper_config_path)
            logger.info("Piper TTS loaded.")
        return True

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes to text using Faster Whisper."""
        self._ensure_whisper()
        
        # Whisper requires a file-like object or numpy array
        # We'll save it to a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name
            
        try:
            segments, info = self.whisper_model.transcribe(temp_audio_path, beam_size=5)
            text = " ".join([segment.text for segment in segments]).strip()
            return text
        finally:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)

    async def synthesize_speech(self, text: str) -> AsyncGenerator[bytes, None]:
        """Synthesize text to speech using Piper TTS and yield audio chunks."""
        if not self._ensure_piper():
            raise RuntimeError("Piper TTS model is not available.")
            
        # Piper yields raw 16-bit PCM audio chunks
        # We wrap it in a WAV container so the browser can play it easily
        
        # Synthesize audio to a memory buffer
        # A more advanced implementation would stream the raw chunks directly to the client
        # with a streaming WAV header, but for simplicity we'll generate it all, then stream.
        
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_path = temp_wav.name
            
        try:
            with wave.open(temp_path, "wb") as wav_file:
                self.piper_voice.synthesize_wav(text, wav_file)
                
            # Stream the generated file back
            with open(temp_path, "rb") as f:
                while chunk := f.read(4096):
                    yield chunk
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

voice_service = VoiceService()
