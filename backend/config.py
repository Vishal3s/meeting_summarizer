import os
from pathlib import Path
from pydantic import BaseModel
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    PROJECT_NAME: str = "Rizer AI Meeting Summarizer"
    VERSION: str = "1.2.0"
    API_V1_STR: str = "/api"
    
    # Storage & Chunking settings
    UPLOAD_DIR: Path = UPLOAD_DIR
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "40"))  # Up to 40MB
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
    CHUNK_THRESHOLD_MB: int = 15  # Files > 15MB will be chunked
    CHUNK_THRESHOLD_BYTES: int = CHUNK_THRESHOLD_MB * 1024 * 1024
    
    ALLOWED_EXTENSIONS: set = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".aac"}
    ALLOWED_MIME_TYPES: set = {
        "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
        "audio/m4a", "audio/x-m4a", "audio/ogg", "audio/flac",
        "audio/webm", "audio/aac", "audio/mp4"
    }
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/meetings.db")
    
    # API Keys & Models
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "openai/whisper-large-v3")
    
    # Providers
    ASR_PROVIDER: str = os.getenv("ASR_PROVIDER", "auto")  # auto, gemini, groq, whisper, huggingface
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")  # auto, gemini, groq

settings = Settings()
