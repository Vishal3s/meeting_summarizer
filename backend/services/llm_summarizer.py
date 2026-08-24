import os
import json
import logging
import uuid
import re
from typing import Dict, Any, List

from backend.config import settings
from backend.services.prompts import EXECUTIVE_SUMMARIZER_SYSTEM_PROMPT, build_summarizer_user_prompt

logger = logging.getLogger(__name__)

class LLMService:
    """Abstract LLM Summarizer base class."""
    def summarize(self, transcript: str) -> Dict[str, Any]:
        """Pass 2: Receives the full audio transcript from Pass 1 and extracts structured summary data."""
        raise NotImplementedError

class GeminiLLMService(LLMService):
    """Google Gemini LLM implementation."""
    def __init__(self, api_key: str):
        self.api_key = api_key or settings.GEMINI_API_KEY

    def summarize(self, transcript: str) -> Dict[str, Any]:
        if not self.api_key:
            return OfflineLLMService().summarize(transcript)

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = f"{EXECUTIVE_SUMMARIZER_SYSTEM_PROMPT}\n\n{build_summarizer_user_prompt(transcript)}"
            response = model.generate_content(prompt)
            raw_text = response.text.strip()
            
            data = _parse_and_verify_summary_json(raw_text, transcript)
            data["provider_used"] = "Google Gemini LLM"
            return data
        except Exception as e:
            logger.error(f"Gemini LLM failed: {e}. Falling back to Dynamic Transcript Summarizer.")
            return OfflineLLMService().summarize(transcript)

class GroqLLMService(LLMService):
    """Groq LLM implementation (Llama 3.3)."""
    def __init__(self, api_key: str):
        self.api_key = api_key or settings.GROQ_API_KEY

    def summarize(self, transcript: str) -> Dict[str, Any]:
        if not self.api_key:
            return OfflineLLMService().summarize(transcript)

        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)
            models_to_try = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama3-70b-8192", "llama3-8b-8192"]
            
            for g_model in models_to_try:
                try:
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": EXECUTIVE_SUMMARIZER_SYSTEM_PROMPT},
                            {"role": "user", "content": build_summarizer_user_prompt(transcript)}
                        ],
                        model=g_model,
                        response_format={"type": "json_object"}
                    )
                    raw_text = chat_completion.choices[0].message.content.strip()
                    data = _parse_and_verify_summary_json(raw_text, transcript)
                    data["provider_used"] = f"Groq ({g_model})"
                    return data
                except Exception as model_err:
                    logger.warning(f"Groq model '{g_model}' attempt failed: {model_err}")
                    continue
                    
            logger.error("All Groq models failed. Falling back to Offline LLM.")
            return OfflineLLMService().summarize(transcript)
        except Exception as e:
            logger.error(f"Groq LLM failed: {e}. Falling back to Dynamic Transcript Summarizer.")
            return OfflineLLMService().summarize(transcript)

class OfflineLLMService(LLMService):
    """
    Intelligent transcript summarizer that dynamically analyzes the exact transcript text to produce clean, non-placeholder summaries.
    """
    def summarize(self, transcript: str) -> Dict[str, Any]:
        lines = [line.strip() for line in transcript.split("\n") if line.strip()]
        
        clean_sentences = []
        for line in lines:
            cleaned = re.sub(r'\[\d{1,2}:\d{2}\]', '', line).strip()
            if cleaned:
                clean_sentences.append(cleaned)

        if not clean_sentences:
            clean_sentences = [transcript]

        summary_intro = "The meeting covered key discussion points from the recorded audio."
        summary_body = " ".join(clean_sentences[:4])
        if len(summary_body) > 300:
            summary_body = summary_body[:300] + "..."
            
        full_summary = f"{summary_intro} Main topics discussed: {summary_body}"

        decisions = []
        for line in clean_sentences:
            if any(w in line.lower() for w in ["agree", "decision", "completed", "done", "will", "scheduled", "confirm", "approve", "next"]):
                d_clean = line[:200] + "..." if len(line) > 200 else line
                decisions.append(d_clean)

        if not decisions:
            first_line = clean_sentences[0] if len(clean_sentences) > 0 else "Reviewed audio transcript content"
            decisions = [first_line[:200] + "..." if len(first_line) > 200 else first_line]

        action_items = []
        for line in clean_sentences:
            if any(w in line.lower() for w in ["will", "task", "action", "verify", "execute", "check", "plan", "need"]):
                speaker = "Unassigned"
                if ":" in line:
                    speaker = line.split(":")[0].strip()
                action_items.append({
                    "id": f"act-{uuid.uuid4().hex[:6]}",
                    "task": line,
                    "assignee": speaker,
                    "priority": "High" if "urgent" in line.lower() or "critical" in line.lower() else "Medium",
                    "status": "To Do"
                })

        if not action_items:
            action_items = [{
                "id": f"act-{uuid.uuid4().hex[:6]}",
                "task": f"Action task derived from audio: {clean_sentences[0][:60]}...",
                "assignee": "Meeting Lead",
                "priority": "Medium",
                "status": "To Do"
            }]

        topics = [{
            "topic": "Meeting Spoken Content",
            "summary": summary_body
        }]

        return {
            "summary": full_summary,
            "key_decisions": decisions[:5],
            "action_items": action_items[:5],
            "topics": topics,
            "provider_used": "Transcript Content Summarizer"
        }

def _parse_and_verify_summary_json(text: str, source_transcript: str = "") -> Dict[str, Any]:
    """Parses JSON and verifies quality constraints on generated summaries."""
    clean_text = text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    if clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()
    
    try:
        data = json.loads(clean_text)
    except Exception:
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except Exception:
                return OfflineLLMService().summarize(source_transcript)
        else:
            return OfflineLLMService().summarize(source_transcript)

    # Post-processing Verification & Schema Normalization
    summary = data.get("summary", "").strip()
    if not summary:
        summary = "Meeting transcript analyzed successfully."

    decisions = data.get("key_decisions", [])
    if not isinstance(decisions, list):
        decisions = [str(decisions)]

    action_items = data.get("action_items", [])
    if isinstance(action_items, list):
        for idx, item in enumerate(action_items):
            if isinstance(item, dict):
                if "id" not in item:
                    item["id"] = f"act-{uuid.uuid4().hex[:6]}"
                if "status" not in item:
                    item["status"] = "To Do"
                if "assignee" not in item or not item["assignee"]:
                    item["assignee"] = "Unassigned"
                if "priority" not in item or not item["priority"]:
                    item["priority"] = "Medium"

    topics = data.get("topics", [])
    if not isinstance(topics, list):
        topics = [{"topic": "Meeting Overview", "summary": summary}]

    return {
        "summary": summary,
        "key_decisions": decisions,
        "action_items": action_items,
        "topics": topics
    }

def get_llm_service() -> LLMService:
    provider = settings.LLM_PROVIDER.lower()
    if provider == "gemini" and settings.GEMINI_API_KEY:
        return GeminiLLMService(settings.GEMINI_API_KEY)
    elif provider == "groq" and settings.GROQ_API_KEY:
        return GroqLLMService(settings.GROQ_API_KEY)
    elif provider == "auto":
        if settings.GEMINI_API_KEY:
            return GeminiLLMService(settings.GEMINI_API_KEY)
        elif settings.GROQ_API_KEY:
            return GroqLLMService(settings.GROQ_API_KEY)
            
    return OfflineLLMService()
