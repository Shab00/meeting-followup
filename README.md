# meeting-followup

A FastAPI + LangGraph service that turns meeting action items into follow-up messages that wait for human approval before being (simulated) sent.

## Setup

```bash
conda create -n meeting-followup python=3.11
conda activate meeting-followup
pip install -r requirements.txt
cp .env.example .env        # then fill in DATABASE_URL, CHECKPOINT_DB_URL, OPENAI_API_KEY
uvicorn app.main:app --reload --port 8002
```

Requires a Postgres database (`meeting_followup` on localhost:5432 by default). Tables are created on startup.

Run tests (OpenAI is mocked; Postgres is real):

```bash
python -m pytest tests/ -v
```

## API

| Method | Path                            | Description                                                   |
|--------|---------------------------------|---------------------------------------------------------------|
| POST   | `/workflows`                    | Start a workflow from action items; returns drafts, `pending_approval` |
| GET    | `/workflows`                    | List workflows (newest first)                                 |
| GET    | `/workflows/{id}`               | Get one workflow with its drafts                              |
| POST   | `/workflows/{id}/approve`       | Approve → resumes the graph → `sent` (simulated)              |
| POST   | `/workflows/{id}/reject`        | Reject → resumes the graph → `rejected`                       |
| GET    | `/health`                       | Liveness check                                                |

POST endpoints are rate-limited to 10/minute per client IP.

## Design decisions

- **LangGraph for orchestration.** The workflow is `draft_followup → wait_for_approval → mark_sent | mark_rejected`.
- **Postgres checkpointer so workflows survive restarts.** `PostgresSaver` stores graph state per workflow (`thread_id` = workflow id). A workflow paused for approval can be resumed by a different process after a restart.
- **`interrupt_before` for human-in-the-loop.** The graph pauses before `wait_for_approval`. Approve/reject writes the decision with `graph.update_state(...)` and resumes with `graph.invoke(None, ...)`. Routing fails closed: anything other than an explicit approve goes to `mark_rejected`.
- **Two stores.** The API writes to both the LangGraph checkpoint and a separate `workflows` table, so listing and fetching are fast and don't replay graph state.

## A2A (partial)

`a2a_client/` calls meeting-processor's A2A server (`MEETING_PROCESSOR_A2A_URL`, default `http://localhost:8000`). `app/graph/tools.py` wraps it as an async LangGraph/LangChain tool, `analyse_meeting_a2a(transcript) -> dict`, which can be used in a `ToolNode` or with `bind_tools`.

a2a_client is currently duplicated across meeting-chat and meeting-followup; extract to a shared package as a follow-up.

Verified: the client on its own, the tool inside an async `ToolNode` graph, and a manual pipeline (A2A analysis, then its `action_items` passed to `POST /workflows`).

**TODO: the tool is not wired into the workflow graph yet.** This service never called meeting-processor before (no REST call to replace), and the end-to-end wiring is blocked by:

1. **No transcript input.** `POST /workflows` and `WorkflowState` take action items that were already extracted. Accepting a transcript means a new request field and state key, which changes the existing endpoint and state schema.
2. **Sync graph.** The graph uses the sync `PostgresSaver` and `graph.invoke` from sync route handlers. An async node that awaits the A2A client needs `AsyncPostgresSaver`, `ainvoke`, and async handlers.
3. **No LLM tool binding.** `draft_followup` calls OpenAI directly, once per action item, so there is no existing `bind_tools` site to add the tool to.

Suggested follow-up: add an optional `transcript` field and an async `analyse` node before `draft_followup` that fills `action_items` from the A2A result (stored as a plain dict), as part of moving to `AsyncPostgresSaver`.

## Not here yet

- Real email sending (sending is simulated)
- A2A wired into the workflow graph (see TODO above)
- Render deploy
