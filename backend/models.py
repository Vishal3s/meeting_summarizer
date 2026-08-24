import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, JSON, DateTime
from backend.database import Base

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    audio_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    duration_seconds = Column(Float, default=0.0)
    
    # Status: pending, transcribing, summarizing, completed, failed
    status = Column(String, default="pending", nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Content
    transcript = Column(Text, nullable=True)
    transcript_segments = Column(JSON, nullable=True)  # List of {start, end, text}
    
    # LLM Results
    summary = Column(Text, nullable=True)
    key_decisions = Column(JSON, nullable=True)  # List of strings
    action_items = Column(JSON, nullable=True)   # List of {id, task, assignee, priority, status}
    topics = Column(JSON, nullable=True)         # List of {topic, summary}
    
    # Metadata
    asr_provider_used = Column(String, nullable=True)
    llm_provider_used = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "filename": self.filename,
            "audio_path": self.audio_path,
            "file_size_bytes": self.file_size_bytes,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "error_message": self.error_message,
            "transcript": self.transcript,
            "transcript_segments": self.transcript_segments or [],
            "summary": self.summary,
            "key_decisions": self.key_decisions or [],
            "action_items": self.action_items or [],
            "topics": self.topics or [],
            "asr_provider_used": self.asr_provider_used,
            "llm_provider_used": self.llm_provider_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
