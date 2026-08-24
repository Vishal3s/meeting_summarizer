import io
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.rag_service import rag_service, LangChainKnowledgeBuilder

client = TestClient(app)

SAMPLE_TRANSCRIPT = (
    "Well, this is the kickoff meeting for our project designing a new remote control. "
    "Laura is project manager, David is industrial designer, Andrew is marketing expert, and Greg is user interface specialist. "
    "The 25 euro remote control might be a big hit in London. Cost target is no more than 12.50 euros."
)

def test_one_line_summary():
    res = rag_service.answer_question(
        question="one line summary",
        transcript=SAMPLE_TRANSCRIPT
    )
    assert "answer" in res
    answer = res["answer"]
    assert len(answer.split("\n")) == 1
    assert "remote control" in answer.lower()


def test_budget_query():
    res = rag_service.answer_question(
        question="What is the project budget?",
        transcript=SAMPLE_TRANSCRIPT
    )
    assert "answer" in res
    answer = res["answer"]
    assert "25" in answer or "12" in answer or "euro" in answer.lower()


def test_tasks_query():
    res = rag_service.answer_question(
        question="What tasks were assigned?",
        transcript=SAMPLE_TRANSCRIPT,
        action_items=[
            {"task": "Lead project management and timelines", "assignee": "Laura"},
            {"task": "Lead industrial design of remote control", "assignee": "David"}
        ]
    )
    assert "laura" in res["answer"].lower() or "david" in res["answer"].lower() or "design" in res["answer"].lower()


def test_missing_info_fallback():
    res = rag_service.answer_question(
        question="What is the quantum physics formula discussed?",
        transcript=SAMPLE_TRANSCRIPT
    )
    assert "does not contain enough information" in res["answer"].lower()


def test_qa_api_endpoint():
    fake_audio = io.BytesIO(b"ID3" + b"\x00" * 2000)
    upload_res = client.post(
        "/api/meetings/upload",
        files={"file": ("qa_test_meeting.mp3", fake_audio, "audio/mpeg")},
        data={"title": "RAG Verification Test Meeting"}
    )
    assert upload_res.status_code == 201
    meeting_id = upload_res.json()["id"]

    qa_res = client.post(
        f"/api/meetings/{meeting_id}/qa",
        json={"question": "one line summary"}
    )
    assert qa_res.status_code == 200
    qa_data = qa_res.json()
    assert qa_data["question"] == "one line summary"
    assert len(qa_data["answer"]) > 10

    del_res = client.delete(f"/api/meetings/{meeting_id}")
    assert del_res.status_code == 204
