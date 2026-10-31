from openai import OpenAI

from app.config import settings
from app.models import WorkflowState

_client = OpenAI(api_key=settings.openai_api_key)


def draft_followup(state: WorkflowState) -> dict:
    """For each action item, generate a short professional follow-up message."""
    drafts = []
    for item in state.get("action_items", []):
        due_clause = (
            f"The due date is {item['due_date']}."
            if item.get("due_date")
            else "No specific due date was set."
        )
        prompt = (
            f"Write a short follow-up message (2 sentences maximum) to "
            f"{item['owner']} about this task from a recent meeting: "
            f"{item['task']}.\n\n"
            f"{due_clause}\n\n"
            f"Rules:\n"
            f"- Reference the task by name. Do not call it 'the action item'.\n"
            f"- Do not use these phrases: 'I hope this message finds you well', "
            f"'I wanted to follow up on', 'please let me know if you need any "
            f"assistance', 'Best regards', 'Thank you'.\n"
            f"- Assume {item['owner']} already knows the context. You are "
            f"reminding them, not introducing the topic.\n"
            f"- Sound like a colleague, not a template.\n"
            f"- Return only the message body. No greeting line, no sign-off."
        )
        resp = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
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
