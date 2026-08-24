import io
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_list_meetings_empty():
    response = client.get("/api/meetings")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "meetings" in data


def test_upload_invalid_file_extension():
    fake_file = io.BytesIO(b"dummy pdf data")
    response = client.post(
        "/api/meetings/upload",
        files={"file": ("report.pdf", fake_file, "application/pdf")}
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_upload_and_process_valid_meeting():
    fake_audio = io.BytesIO(b"ID3" + b"\x00" * 2000)
    response = client.post(
        "/api/meetings/upload",
        files={"file": ("test_meeting.mp3", fake_audio, "audio/mpeg")},
        data={"title": "Test Sprint Review"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Sprint Review"
    assert data["status"] == "completed"
    assert data["summary"] is not None
    assert len(data["action_items"]) > 0

    meeting_id = data["id"]

    # Test Get Meeting Details
    get_res = client.get(f"/api/meetings/{meeting_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == meeting_id

    # Test Patch Action Item Status
    action_item_id = data["action_items"][0]["id"]
    patch_res = client.patch(
        f"/api/meetings/{meeting_id}/action-items",
        json={"action_item_id": action_item_id, "status": "Done"}
    )
    assert patch_res.status_code == 200
    updated_actions = patch_res.json()["action_items"]
    assert any(item["id"] == action_item_id and item["status"] == "Done" for item in updated_actions)

    # Test Export Markdown
    export_res = client.get(f"/api/meetings/{meeting_id}/export?format=markdown")
    assert export_res.status_code == 200
    assert "# Test Sprint Review" in export_res.text
    assert "Executive Summary" in export_res.text

    # Test Export JSON
    export_json = client.get(f"/api/meetings/{meeting_id}/export?format=json")
    assert export_json.status_code == 200
    assert "Test Sprint Review" in export_json.text

    # Test Export Text (.txt)
    export_txt = client.get(f"/api/meetings/{meeting_id}/export?format=text")
    assert export_txt.status_code == 200
    assert "=== TEST SPRINT REVIEW ===" in export_txt.text
    assert "[FULL TRANSCRIPT]" in export_txt.text

    # Test Export Raw Transcript (.txt)
    export_transcript = client.get(f"/api/meetings/{meeting_id}/export?format=transcript")
    assert export_transcript.status_code == 200

    # Test Delete Meeting
    del_res = client.delete(f"/api/meetings/{meeting_id}")
    assert del_res.status_code == 204
