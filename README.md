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

## Not here yet

- Real email sending (sending is simulated)
- A2A integration
- Render deploy
