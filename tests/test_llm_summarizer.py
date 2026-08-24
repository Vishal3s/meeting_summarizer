import pytest
from backend.services.llm_summarizer import OfflineLLMService, _parse_json_response

def test_offline_llm_service():
    service = OfflineLLMService()
    result = service.summarize("Sample meeting transcript text")
    
    assert "summary" in result
    assert isinstance(result["summary"], str)
    assert len(result["summary"]) > 0
    
    assert "key_decisions" in result
    assert isinstance(result["key_decisions"], list)
    
    assert "action_items" in result
    assert isinstance(result["action_items"], list)
    assert len(result["action_items"]) > 0
    assert "id" in result["action_items"][0]
    assert "task" in result["action_items"][0]


def test_parse_json_response_clean():
    raw_json = """
    {
      "summary": "The team agreed on launching the beta next week.",
      "key_decisions": ["Launch beta on Monday"],
      "action_items": [{"task": "Prepare release notes", "assignee": "Alice", "priority": "High"}],
      "topics": [{"topic": "Release", "summary": "Discussed timing"}]
    }
    """
    parsed = _parse_json_response(raw_json)
    assert parsed["summary"] == "The team agreed on launching the beta next week."
    assert len(parsed["key_decisions"]) == 1
    assert len(parsed["action_items"]) == 1
    assert "id" in parsed["action_items"][0]


def test_parse_json_response_with_markdown_fences():
    raw_fence = """```json
    {
      "summary": "Fenced summary test.",
      "key_decisions": ["Decision 1"],
      "action_items": []
    }
    ```"""
    parsed = _parse_json_response(raw_fence)
    assert parsed["summary"] == "Fenced summary test."
    assert parsed["key_decisions"] == ["Decision 1"]
