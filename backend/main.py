import os
import sys
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import uuid
import shutil
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import engine, Base, get_db
from backend.models import Meeting
from backend.schemas import (
    MeetingResponse, MeetingListResponse, ActionItemUpdate, SummaryResultSchema,
    QARequest, QAResponse
)
from backend.services.audio_validator import AudioValidator, AudioValidationError
from backend.services.audio_processor import AudioProcessor
from backend.services.audio_chunker import AudioChunker
from backend.services.asr_service import get_asr_service
from backend.services.llm_summarizer import get_llm_service
from backend.services.exporter import MeetingExporter
from backend.services.rag_service import rag_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meeting_summarizer")

# Initialize SQLite database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Reticla AI Meeting Summarizer Application API"
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure Directories Exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

# Mount Uploaded Audio Files
app.mount("/media", StaticFiles(directory=settings.UPLOAD_DIR), name="media")


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "chunk_threshold_mb": settings.CHUNK_THRESHOLD_MB,
        "whisper_model": settings.WHISPER_MODEL,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "groq_configured": bool(settings.GROQ_API_KEY),
        "active_asr_provider": settings.ASR_PROVIDER,
        "active_llm_provider": settings.LLM_PROVIDER
    }


@app.post("/api/meetings/upload", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_process_meeting(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    2-Pass Audio & Summary Pipeline:
    - Preprocessing: Audio normalization & 16kHz resampling for peak ASR accuracy.
    - Pass 1: Ingests audio (up to 40MB, overlapping chunks if >15MB) and extracts 100% spoken transcript via openai/whisper-large-v3.
    - Pass 2: Feeds the extracted transcript into LLM via prompt engineering to produce precise summary, key decisions, and action items.
    """
    filename = file.filename or "uploaded_audio.mp3"
    meeting_title = title.strip() if title and title.strip() else Path(filename).stem.replace("_", " ").replace("-", " ").title()

    contents = await file.read()
    file_size = len(contents)

    # Validate Audio
    try:
        is_valid, validation_msg = AudioValidator.validate_file(filename=filename, file_size=file_size, content_type=file.content_type)
        logger.info(f"Validation success for '{filename}': {validation_msg}")
    except AudioValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save File
    file_id = str(uuid.uuid4())
    ext = Path(filename).suffix.lower()
    saved_filename = f"{file_id}{ext}"
    saved_path = settings.UPLOAD_DIR / saved_filename

    with open(saved_path, "wb") as f:
        f.write(contents)

    meeting = Meeting(
        id=file_id,
        title=meeting_title,
        filename=filename,
        audio_path=f"/media/{saved_filename}",
        file_size_bytes=file_size,
        status="processing"
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    try:
        # Preprocessing: Optimize audio format & sample rate for ASR accuracy
        processed_audio_path = AudioProcessor.prepare_audio_for_asr(str(saved_path))

        # Pass 1: Complete Audio Content Extraction (ASR Speech Engine)
        chunks = AudioChunker.chunk_audio_file(processed_audio_path)
        num_chunks = len(chunks)
        
        asr_service = get_asr_service()
        logger.info(f"PASS 1 START: Transcribing full content for file '{filename}' using {settings.WHISPER_MODEL}...")
        
        if num_chunks > 1:
            asr_result = asr_service.transcribe_chunks(chunks)
        else:
            asr_result = asr_service.transcribe(processed_audio_path)

        transcript_text = asr_result.get("transcript", "").strip()
        segments = asr_result.get("segments", [])
        asr_provider = asr_result.get("provider_used", "openai/whisper-large-v3")

        # Cleanup temporary 16k audio file if created
        AudioProcessor.cleanup_temp_audio(processed_audio_path, str(saved_path))

        if not transcript_text:
            raise ValueError("ASR engine produced empty transcript. Ensure valid audio content.")

        meeting.transcript = transcript_text
        meeting.transcript_segments = segments
        meeting.asr_provider_used = asr_provider

        if segments:
            meeting.duration_seconds = max([seg.get("end", 0.0) for seg in segments], default=0.0)
        else:
            meeting.duration_seconds = 60.0 * num_chunks

        # Pass 2: Transcript-bound LLM Summarization & Action Extraction
        logger.info(f"PASS 2 START: Processing full transcript content through prompt-engineered LLM summarizer...")
        llm_service = get_llm_service()
        llm_result = llm_service.summarize(transcript_text)

        meeting.summary = llm_result.get("summary", "")
        meeting.key_decisions = llm_result.get("key_decisions", [])
        meeting.action_items = llm_result.get("action_items", [])
        meeting.topics = llm_result.get("topics", [])
        meeting.llm_provider_used = llm_result.get("provider_used", "Executive LLM Engine")
        meeting.status = "completed"

        db.commit()
        db.refresh(meeting)
        return meeting.to_dict()

    except Exception as e:
        logger.error(f"Error processing meeting {file_id}: {e}")
        meeting.status = "failed"
        meeting.error_message = str(e)
        db.commit()
        db.refresh(meeting)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/api/meetings/{meeting_id}/process", response_model=MeetingResponse)
def reprocess_meeting(meeting_id: str, db: Session = Depends(get_db)):
    """Compatibility route endpoint for meeting processing."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting.to_dict()


@app.get("/api/meetings", response_model=MeetingListResponse)
def list_meetings(
    search: Optional[str] = Query(None, description="Search query for title, transcript, or summary"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Meeting)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Meeting.title.ilike(search_pattern)) |
            (Meeting.transcript.ilike(search_pattern)) |
            (Meeting.summary.ilike(search_pattern))
        )
    
    total = query.count()
    meetings = query.order_by(Meeting.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "meetings": [m.to_dict() for m in meetings]
    }


@app.get("/api/meetings/{meeting_id}", response_model=MeetingResponse)
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting.to_dict()


@app.patch("/api/meetings/{meeting_id}/action-items", response_model=MeetingResponse)
def update_action_item_status(
    meeting_id: str,
    payload: ActionItemUpdate,
    db: Session = Depends(get_db)
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    action_items = meeting.action_items or []
    updated = False
    for item in action_items:
        if item.get("id") == payload.action_item_id:
            item["status"] = payload.status
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Action item ID not found")

    meeting.action_items = list(action_items)
    db.commit()
    db.refresh(meeting)
    return meeting.to_dict()


@app.delete("/api/meetings/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.filename:
        file_path = settings.UPLOAD_DIR / Path(meeting.audio_path).name
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Could not remove audio file {file_path}: {e}")

    db.delete(meeting)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/meetings/{meeting_id}/export")
def export_meeting(
    meeting_id: str,
    format: str = Query("markdown", description="Export format: markdown, json, or text"),
    db: Session = Depends(get_db)
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    m_dict = meeting.to_dict()
    title_slug = "".join([c if c.isalnum() else "_" for c in meeting.title]).lower()

    if format.lower() == "json":
        content = MeetingExporter.to_json(m_dict)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{title_slug}_summary.json"'}
        )
    elif format.lower() == "text":
        content = MeetingExporter.to_text(m_dict)
        return PlainTextResponse(
            content=content,
            headers={"Content-Disposition": f'attachment; filename="{title_slug}_summary.txt"'}
        )
    else:
        content = MeetingExporter.to_markdown(m_dict)
        return PlainTextResponse(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{title_slug}_summary.md"'}
        )


@app.post("/api/meetings/{meeting_id}/qa", response_model=QAResponse)
def qa_meeting_transcript(
    meeting_id: str,
    payload: QARequest,
    db: Session = Depends(get_db)
):
    """
    RAG Transcript Q&A Endpoint:
    Uses LangChain Document/VectorStore & LangGraph state graph execution
    over meeting transcripts, decisions, and action items to retrieve relevant context
    and generate context-bound answers with speaker and timestamp citations.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.transcript and not meeting.summary:
        raise HTTPException(status_code=400, detail="Meeting record is empty or unavailable.")

    result = rag_service.answer_question(
        question=payload.question,
        transcript=meeting.transcript,
        segments=meeting.transcript_segments,
        summary=meeting.summary,
        key_decisions=meeting.key_decisions,
        action_items=meeting.action_items,
        topics=meeting.topics
    )
    return result


if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
