from openai import OpenAI

from app.config import settings
from app.models import WorkflowState

_client = OpenAI(api_key=settings.openai_api_key)


def draft_followup(state: WorkflowState) -> dict:
    """For each action item, generate a short professional follow-up message."""
    drafts = []
    for item in state.get("action_items", []):
        prompt = (
            f"Write a short (2-3 sentence) professional follow-up message to "
            f"{item['owner']} about the action item: {item['task']}. "
            f"Due: {item.get('due_date') or 'no specific date'}. "
            f"Tone: polite, direct. No subject line, just the message body."
        )
        resp = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        drafts.append({
            "owner": item["owner"],
            "task": item["task"],
            "message": resp.choices[0].message.content.strip(),
        })
    return {"drafts": drafts, "status": "pending_approval"}


def wait_for_approval(state: WorkflowState) -> dict:
    """No-op node — the interrupt is placed BEFORE this node in the graph.
    When the graph resumes after approval, control returns here and then
    proceeds to mark_sent / mark_rejected. State is left unchanged."""
    return {}


def mark_sent(state: WorkflowState) -> dict:
    # Sending is simulated — no real email goes out.
    return {"status": "sent"}


def mark_rejected(state: WorkflowState) -> dict:
    return {"status": "rejected"}
