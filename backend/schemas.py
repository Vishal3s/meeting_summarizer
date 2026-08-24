from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class TranscriptSegment(BaseModel):
    start: float = Field(..., description="Start timestamp in seconds")
    end: float = Field(..., description="End timestamp in seconds")
    text: str = Field(..., description="Transcript text segment")

class ActionItemSchema(BaseModel):
    id: str = Field(..., description="Unique action item ID")
    task: str = Field(..., description="Task description")
    assignee: Optional[str] = Field("Unassigned", description="Task assignee")
    priority: Optional[str] = Field("Medium", description="High, Medium, Low")
    status: str = Field("To Do", description="To Do, In Progress, Done")

class TopicSchema(BaseModel):
    topic: str = Field(..., description="Topic headline")
    summary: str = Field(..., description="Brief discussion summary")

class MeetingBase(BaseModel):
    title: str

class ActionItemUpdate(BaseModel):
    action_item_id: str
    status: str  # "To Do", "In Progress", "Done"

class SummaryResultSchema(BaseModel):
    summary: str
    key_decisions: List[str] = []
    action_items: List[ActionItemSchema] = []
    topics: List[TopicSchema] = []

class MeetingResponse(BaseModel):
    id: str
    title: str
    filename: str
    audio_path: Optional[str] = None
    file_size_bytes: int
    duration_seconds: float
    status: str
    error_message: Optional[str] = None
    transcript: Optional[str] = None
    transcript_segments: List[TranscriptSegment] = []
    summary: Optional[str] = None
    key_decisions: List[str] = []
    action_items: List[ActionItemSchema] = []
    topics: List[TopicSchema] = []
    asr_provider_used: Optional[str] = None
    llm_provider_used: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class MeetingListResponse(BaseModel):
    total: int
    meetings: List[MeetingResponse]

class QARequest(BaseModel):
    question: str = Field(..., description="User question about the meeting transcript")

class QASourceChunk(BaseModel):
    text: str
    start: float = 0.0
    end: float = 0.0
    timestamp_str: str = ""
    speaker: str = "Unknown"

class QAResponse(BaseModel):
    question: str
    answer: str
    sources: List[QASourceChunk] = []
    provider_used: str = "RAG Engine"
