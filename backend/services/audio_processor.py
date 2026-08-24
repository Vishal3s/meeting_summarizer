import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class AudioProcessor:
    """
    Preprocesses audio files to maximize Speech-to-Text (ASR) transcription accuracy.
    Converts audio to 16kHz mono WAV for optimal input to Whisper / Speech models.
    """

    @staticmethod
    def prepare_audio_for_asr(audio_path: str) -> str:
        """
        Normalizes audio sample rate to 16000Hz mono WAV if pydub/ffmpeg is available.
        Returns path to processed audio file (or original path if already optimal).
        """
        path_obj = Path(audio_path)
        if not path_obj.exists():
            return audio_path

        # If already 16kHz mono wav temp file, return
        if audio_path.endswith("_16k.wav"):
            return audio_path

        try:
            from pydub import AudioSegment
            logger.info(f"Preprocessing audio '{path_obj.name}' for maximum ASR transcription accuracy...")
            sound = AudioSegment.from_file(audio_path)
            
            # Normalize to 16kHz, 1 channel (mono)
            sound = sound.set_frame_rate(16000).set_channels(1)
            
            processed_path = path_obj.parent / f"{path_obj.stem}_16k.wav"
            sound.export(str(processed_path), format="wav")
            
            logger.info(f"Audio normalized to 16kHz mono WAV: {processed_path.name}")
            return str(processed_path)
            
        except Exception as e:
            logger.info(f"Audio preprocessing note: {e}. Using original audio file.")
            return audio_path

    @staticmethod
    def cleanup_temp_audio(processed_path: str, original_path: str):
        """Cleans up temporary preprocessed 16k WAV files."""
        if processed_path != original_path and os.path.exists(processed_path):
            try:
                os.remove(processed_path)
            except Exception as e:
                logger.warning(f"Could not remove temp audio file {processed_path}: {e}")
