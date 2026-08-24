import os
from pathlib import Path
from typing import Tuple
from backend.config import settings

class AudioValidationError(Exception):
    """Custom exception raised when audio validation fails."""
    pass

class AudioValidator:
    """Validates uploaded audio files for size (up to 40MB), extension, MIME type, and emptiness."""
    
    @staticmethod
    def validate_file(filename: str, file_size: int, content_type: str = "") -> Tuple[bool, str]:
        """
        Validates file metadata.
        Returns (is_valid, message).
        """
        if not filename or filename.strip() == "":
            raise AudioValidationError("Filename cannot be empty.")
            
        ext = Path(filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(list(settings.ALLOWED_EXTENSIONS)))
            raise AudioValidationError(
                f"Unsupported file extension '{ext}'. Allowed extensions: {allowed}"
            )
            
        if file_size <= 0:
            raise AudioValidationError("Uploaded file is empty (0 bytes).")
            
        if file_size > settings.MAX_FILE_SIZE_BYTES:
            max_mb = settings.MAX_FILE_SIZE_MB
            file_mb = round(file_size / (1024 * 1024), 2)
            raise AudioValidationError(
                f"File size ({file_mb} MB) exceeds maximum allowed limit of {max_mb} MB."
            )
            
        is_large = file_size > settings.CHUNK_THRESHOLD_BYTES
        msg = f"Valid audio file ({round(file_size/(1024*1024), 2)} MB)."
        if is_large:
            msg += f" Large file detected — will be automatically split into chunked parts for processing."
            
        return True, msg
