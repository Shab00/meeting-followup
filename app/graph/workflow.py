from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver

from app.config import settings
from app.models import WorkflowState
from app.graph import nodes

# PostgresSaver requires these connection settings (same as its own
# from_conn_string): autocommit for setup()'s DDL, dict_row because it reads
# rows by column name, prepare_threshold=0 to avoid prepared-statement clashes.
# A pool (rather than one connection) survives Postgres-side disconnects.
_pool = ConnectionPool(
    conninfo=settings.checkpoint_db_url,
    kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    min_size=1,
    max_size=10,
    open=True,
)
checkpointer = PostgresSaver(_pool)

# Create checkpoint tables / run migrations once, before any workflow runs.
checkpointer.setup()


def _route_after_wait(state: WorkflowState) -> str:
    """Route based on the decision recorded by the API when resuming.
    Fails closed: anything other than an explicit approve is a reject."""
    if state.get("decision") == "approve":
        return "approve"
    return "reject"


def _draft_followup(state: WorkflowState) -> dict:
    # Look up nodes.draft_followup at call time so tests can monkeypatch it.
    return nodes.draft_followup(state)


def build_graph():
    builder = StateGraph(WorkflowState)
    builder.add_node("draft_followup", _draft_followup)
    builder.add_node("wait_for_approval", nodes.wait_for_approval)
    builder.add_node("mark_sent", nodes.mark_sent)
    builder.add_node("mark_rejected", nodes.mark_rejected)

    builder.add_edge(START, "draft_followup")
    builder.add_edge("draft_followup", "wait_for_approval")

    builder.add_conditional_edges(
        "wait_for_approval",
        _route_after_wait,
        {"approve": "mark_sent", "reject": "mark_rejected"},
    )

    builder.add_edge("mark_sent", END)
    builder.add_edge("mark_rejected", END)

    # interrupt_before pauses the graph BEFORE running wait_for_approval.
    # So draft_followup runs → graph pauses → API returns pending_approval.
    # On resume, wait_for_approval runs → conditional routes to mark_sent/rejected.
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["wait_for_approval"],
    )


graph = build_graph()
