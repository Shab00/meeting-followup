import os

from dotenv import load_dotenv

load_dotenv()  # real local creds, if present; setdefault below is the fallback
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/meeting_followup")
os.environ.setdefault("CHECKPOINT_DB_URL", "postgresql://postgres:postgres@localhost:5432/meeting_followup")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("ALLOWED_ORIGIN", "http://localhost:8002")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
