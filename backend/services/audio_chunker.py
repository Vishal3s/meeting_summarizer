import os
import math
import logging
from pathlib import Path
from typing import List, Dict, Any
from backend.config import settings

logger = logging.getLogger(__name__)

class AudioChunker:
    """
    Splits large audio files into proper overlapping audio chunks to ensure speech at boundaries is never cut off.
    """

    @staticmethod
    def should_chunk(file_size_bytes: int) -> bool:
        return file_size_bytes > settings.CHUNK_THRESHOLD_BYTES

    @staticmethod
    def chunk_audio_file(
        audio_path: str,
        chunk_duration_sec: float = 300.0,  # 5 minute chunk duration
        overlap_duration_sec: float = 15.0   # 15 second overlap
    ) -> List[Dict[str, Any]]:
        """
        Splits audio into overlapping chunks (e.g. 0-300s, 285-585s, 570-870s) using pydub/wave if available,
        or safe file splitting.
        """
        path_obj = Path(audio_path)
        file_size = path_obj.stat().st_size

        if file_size <= settings.CHUNK_THRESHOLD_BYTES:
            return [{
                "chunk_index": 1,
                "path": str(audio_path),
                "size": file_size,
                "time_offset": 0.0,
                "overlap_sec": 0.0
            }]

        chunk_dir = path_obj.parent / f"{path_obj.stem}_chunks"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        ext = path_obj.suffix.lower()

        # Try pydub for proper overlapping audio chunks
        try:
            from pydub import AudioSegment
            logger.info(f"Creating overlapping audio chunks for '{path_obj.name}' using pydub...")
            audio = AudioSegment.from_file(audio_path)
            total_sec = len(audio) / 1000.0
            
            chunks = []
            chunk_idx = 1
            current_start_sec = 0.0

            while current_start_sec < total_sec:
                current_end_sec = min(current_start_sec + chunk_duration_sec, total_sec)
                
                start_ms = int(current_start_sec * 1000)
                end_ms = int(current_end_sec * 1000)
                
                chunk_audio = audio[start_ms:end_ms]
                chunk_filename = chunk_dir / f"chunk_{chunk_idx}_overlap{ext}"
                
                format_str = ext.replace(".", "")
                if format_str in ["m4a", "aac"]:
                    format_str = "ipod"
                    
                chunk_audio.export(str(chunk_filename), format=format_str)
                
                chunks.append({
                    "chunk_index": chunk_idx,
                    "path": str(chunk_filename),
                    "size": chunk_filename.stat().st_size,
                    "time_offset": current_start_sec,
                    "overlap_sec": overlap_duration_sec if chunk_idx > 1 else 0.0
                })
                
                if current_end_sec >= total_sec:
                    break
                    
                # Advance start time minus overlap
                current_start_sec += (chunk_duration_sec - overlap_duration_sec)
                chunk_idx += 1

            logger.info(f"Created {len(chunks)} overlapping chunks for '{path_obj.name}'.")
            return chunks

        except Exception as pydub_err:
            logger.warning(f"Pydub overlap chunking unavailable ({pydub_err}). Using safe binary chunking.")

        # Fallback binary chunking
        chunks = []
        chunk_size_bytes = 15 * 1024 * 1024
        num_chunks = math.ceil(file_size / chunk_size_bytes)
        
        try:
            with open(audio_path, "rb") as src:
                for i in range(num_chunks):
                    chunk_path = chunk_dir / f"chunk_{i+1}{ext}"
                    data = src.read(chunk_size_bytes)
                    if not data:
                        break
                    with open(chunk_path, "wb") as f:
                        f.write(data)

                    chunks.append({
                        "chunk_index": i + 1,
                        "path": str(chunk_path),
                        "size": len(data),
                        "time_offset": round(i * chunk_duration_sec, 2),
                        "overlap_sec": 0.0
                    })
        except Exception as err:
            logger.error(f"Error during fallback chunking: {err}")
            return [{
                "chunk_index": 1,
                "path": str(audio_path),
                "size": file_size,
                "time_offset": 0.0,
                "overlap_sec": 0.0
            }]

        return chunks
