import pytest
from backend.services.prompts import EXECUTIVE_SUMMARIZER_SYSTEM_PROMPT, build_summarizer_user_prompt

def test_prompt_content():
    assert "Reticla AI" in EXECUTIVE_SUMMARIZER_SYSTEM_PROMPT
    assert "TRANSCRIPT GROUNDING" in EXECUTIVE_SUMMARIZER_SYSTEM_PROMPT
    assert "action_items" in EXECUTIVE_SUMMARIZER_SYSTEM_PROMPT

def test_build_user_prompt():
    transcript = "Speaker A: We aligned on Q3 goals."
    user_prompt = build_summarizer_user_prompt(transcript)
    assert transcript in user_prompt
    assert "MEETING TRANSCRIPT TO ANALYZE" in user_prompt
