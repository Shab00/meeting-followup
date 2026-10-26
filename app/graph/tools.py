from dotenv import load_dotenv
from langchain_core.tools import tool

from a2a_client import analyse_via_a2a

# pydantic-settings reads .env without exporting it, but a2a_client reads
# MEETING_PROCESSOR_A2A_URL from os.environ. Does not override real env vars.
load_dotenv()


@tool
async def analyse_meeting_a2a(transcript: str) -> dict:
    """Analyse a meeting transcript via meeting-processor's A2A agent.

    Returns a dict with "summary", "action_items", "decisions" and "risks".
    The action_items match this service's ActionItem shape, so they can be
    passed straight into a follow-up workflow.
    On failure, returns {"error": "..."} instead.
    """
    try:
        return await analyse_via_a2a(transcript)
    except RuntimeError as e:
        return {"error": str(e)}
