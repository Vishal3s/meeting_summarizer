# Reticla AI - Meeting Summarizer Platform

A production-ready, full-stack AI Meeting Summarizer application built with **FastAPI**, **SQLite**, and a **Reticla AI dark glassmorphism web dashboard**. Reticla ingests meeting audio files (up to 40MB), preprocesses and chunks audio for peak ASR accuracy, transcribes speech using cloud & local models (`whisper-large-v3` / Gemini 1.5 / Groq / HuggingFace), extracts grounded executive summaries, key decisions, and action items via prompt-engineered LLMs, and presents an interactive UI with RAG semantic search.

---

## 🌟 Key Features

- **Multi-Format Audio Upload (Up to 40MB)**: Supports `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`, `.webm`, and `.aac` with automatic file size, header, and extension validation.
- **Sequential 2-Pass Audio Pipeline**:
  - **Pass 1**: Extract 100% full verbatim spoken transcript (Groq Whisper `whisper-large-v3`, Gemini 1.5 Flash, Hugging Face, Local Whisper, or Google Speech Engine).
  - **Pass 2**: Process full transcript through LLMs to generate non-hallucinated executive summary, key decisions, action tasks, and discussion topics.
- **Reticla Dark Glassmorphism UI**: High-contrast obsidian dark interface with frosted glass panels, glowing coral accents, live stepper progress, and `Cmd/Ctrl + K` global search bar.
- **Interactive Audio & Task Workbench**:
  - **Audio Seek Timestamps**: Clicking any `[MM:SS]` timestamp in the transcript jumps directly to that time in the audio player.
  - **Action Task Management**: Toggle task completion status in real-time with backend SQLite state persistence.
- **RAG Semantic Search**: Ask natural language questions about any uploaded meeting and receive contextually grounded answers with source timestamps.
- **Multi-Format Export**: One-click download as **Markdown (`.md`)**, **JSON**, or **Plain Text (`.txt`)**.

---

## 🏗️ Architecture & Component Overview

| Component | Responsibility | File Reference |
| :--- | :--- | :--- |
| **Config & Environment** | Central settings management & `.env` file loader | [`backend/config.py`](file:///c:/Users/LENOVO/Downloads/Metting%20Summarizer/backend/config.py) |
| **Audio Validator** | Audio format, extension, size (<40MB) and header validation | [`backend/services/audio_validator.py`](file:///c:/Users/LENOVO/Downloads/Metting%20Summarizer/backend/services/audio_validator.py) |
| **Audio Chunker** | Normalizes audio to 16kHz mono WAV & creates 5-min overlapping chunks | [`backend/services/audio_chunker.py`](file:///c:/Users/LENOVO/Downloads/Metting%20Summarizer/backend/services/audio_chunker.py) |
| **ASR Service Engine** | Non-recursive linear fallback chain: `Groq` → `Gemini` → `HuggingFace` → `Local Whisper` → `SpeechRecognition` → `Offline Processor` | [`backend/services/asr_service.py`](file:///c:/Users/LENOVO/Downloads/Metting%20Summarizer/backend/services/asr_service.py) |
| **LLM Summarizer** | Grounded JSON extraction for summary, decisions, & tasks | [`backend/services/llm_summarizer.py`](file:///c:/Users/LENOVO/Downloads/Metting%20Summarizer/backend/services/llm_summarizer.py) |
| **RAG Search Engine** | TF-IDF / BGE vector embeddings for Q&A across meeting history | [`backend/services/rag_service.py`](file:///c:/Users/LENOVO/Downloads/Metting%20Summarizer/backend/services/rag_service.py) |
| **Exporters** | Formats meeting transcripts and summaries to Markdown, JSON, and Text | [`backend/services/exporter.py`](file:///c:/Users/LENOVO/Downloads/Metting%20Summarizer/backend/services/exporter.py) |
| **Frontend Web App** | Single-page HTML/CSS/JS application with dark glassmorphism aesthetic | [`frontend/`](file:///c:/Users/LENOVO/Downloads/Metting%20Summarizer/frontend/) |

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python 3.10** or higher
- **pip** or **uv** package manager

### 2. Clone and Setup Environment
```bash
git clone <your-repository-url>
cd "Metting Summarizer"

# Create virtual environment (optional but recommended)
python -m venv venv

# Activate virtual environment
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. API Key Configuration (Optional)
Copy `.env.example` to `.env` and set your API keys:

```bash
cp .env.example .env
```

Edit your `.env` file:
```env
# Groq API Key (Free key at: https://console.groq.com/)
GROQ_API_KEY=gsk_your_groq_key_here

# Google Gemini API Key (Free key at: https://aistudio.google.com/)
GEMINI_API_KEY=AIzaSy_your_gemini_key_here

# Application Settings
DATABASE_URL=sqlite:///./meetings.db
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=40
ASR_PROVIDER=auto
LLM_PROVIDER=auto
```

> **Note**: If no API keys are set, the application operates in **Offline Fallback Mode** using local processors.

### 4. Run the Application
Launch the FastAPI development server:
```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser and navigate to:
**`http://127.0.0.1:8000`**

---

## 🧪 Running Automated Tests

Run the full Pytest test suite:
```bash
pytest -v
```

---

## 📦 Git & Repository Setup

A complete `.gitignore` is provided to ensure sensitive API keys, local databases, and temporary audio files are **never** committed to Git.

To initialize and push to your remote repository:
```bash
git init
git add .
git commit -m "Initial commit: Reticla AI Meeting Summarizer Platform"
git branch -M main
git remote add origin <your-remote-repository-url>
git push -u origin main
```
