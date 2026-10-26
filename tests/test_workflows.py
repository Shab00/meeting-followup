import os
import uuid

from dotenv import load_dotenv

load_dotenv()  # real local creds, if present; setdefault below is the fallback
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/meeting_followup")
os.environ.setdefault("CHECKPOINT_DB_URL", "postgresql://postgres:postgres@localhost:5432/meeting_followup")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("ALLOWED_ORIGIN", "http://localhost:8002")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.graph import nodes  # noqa: E402
from app.main import app  # noqa: E402

FAKE_DRAFT = {
    "owner": "Carol",
    "task": "Review runway",
    "message": "Hi Carol, a quick reminder to review our runway by Friday. Thanks!",
}

PAYLOAD = {
    "meeting_id": "3a594b29-f479-446c-8141-7c8ee8277e5e",
    "action_items": [{
        "owner": "Carol",
        "task": "Review runway",
        "due_date": "Friday",
        "source_quote": "I will review our runway",
    }],
}


@pytest.fixture
def client(monkeypatch):
    # No real OpenAI calls in tests.
    monkeypatch.setattr(
        nodes, "draft_followup",
        lambda state: {"drafts": [FAKE_DRAFT], "status": "pending_approval"},
    )
    with TestClient(app) as c:
        yield c


def _start(client) -> dict:
    resp = client.post("/workflows", json=PAYLOAD)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_start_workflow_pending_with_drafts(client):
    body = _start(client)
    assert body["status"] == "pending_approval"
    assert body["drafts"] == [FAKE_DRAFT]
    assert body["meeting_id"] == PAYLOAD["meeting_id"]
    assert body["decided_at"] is None


def test_get_workflow(client):
    wf_id = _start(client)["id"]
    resp = client.get(f"/workflows/{wf_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == wf_id
    assert body["status"] == "pending_approval"
    assert body["drafts"] == [FAKE_DRAFT]


def test_approve_transitions_to_sent(client):
    wf_id = _start(client)["id"]
    resp = client.post(f"/workflows/{wf_id}/approve")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "sent"
    assert resp.json()["decided_at"] is not None
    # A decided workflow can't be decided again.
    assert client.post(f"/workflows/{wf_id}/reject").status_code == 400


def test_reject_transitions_to_rejected(client):
    wf_id = _start(client)["id"]
    resp = client.post(f"/workflows/{wf_id}/reject")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"


def test_approve_nonexistent_returns_404(client):
    resp = client.post(f"/workflows/{uuid.uuid4()}/approve")
    assert resp.status_code == 404
