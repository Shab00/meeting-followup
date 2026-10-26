import uuid
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    StartWorkflowRequest, WorkflowOut, WorkflowListItem, Workflow, WorkflowState,
)
from app.graph.workflow import graph

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["workflows"])


def _config(workflow_id: UUID) -> dict:
    return {"configurable": {"thread_id": str(workflow_id)}}


@router.post("/workflows", response_model=WorkflowOut)
@limiter.limit("10/minute")
def start_workflow(
    request: Request,
    req: StartWorkflowRequest,
    db: Session = Depends(get_db),
):
    workflow_id = uuid.uuid4()

    # Persist a row first so GET can find it even if graph execution fails
    wf = Workflow(
        id=workflow_id,
        meeting_id=req.meeting_id,
        status="drafting",
        drafts=[],
    )
    db.add(wf); db.commit(); db.refresh(wf)

    # Run the graph up to the interrupt
    initial_state: WorkflowState = {
        "meeting_id": str(req.meeting_id),
        "action_items": [a.model_dump() for a in req.action_items],
        "drafts": [],
        "decision": None,
        "status": "drafting",
    }
    config = _config(workflow_id)

    try:
        graph.invoke(initial_state, config=config)
    except Exception as e:
        db.delete(wf); db.commit()
        raise HTTPException(status_code=500, detail=f"Graph failed: {e}")

    # After invoke returns, the graph has paused before wait_for_approval
    state = graph.get_state(config)
    wf.drafts = state.values.get("drafts", [])
    wf.status = "pending_approval"
    db.commit(); db.refresh(wf)

    return WorkflowOut.model_validate(wf)


@router.get("/workflows", response_model=list[WorkflowListItem])
def list_workflows(db: Session = Depends(get_db)):
    return db.query(Workflow).order_by(Workflow.created_at.desc()).all()


@router.get("/workflows/{workflow_id}", response_model=WorkflowOut)
def get_workflow(workflow_id: UUID, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowOut.model_validate(wf)


def _decide(workflow_id: UUID, decision: str, db: Session) -> WorkflowOut:
    """Record the human decision in the checkpoint and resume the graph."""
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.status != "pending_approval":
        raise HTTPException(status_code=400, detail=f"Cannot {decision} in status {wf.status}")

    config = _config(workflow_id)
    if "wait_for_approval" not in graph.get_state(config).next:
        raise HTTPException(status_code=409, detail="Workflow checkpoint is not awaiting approval")

    graph.update_state(config, {"decision": decision})
    graph.invoke(None, config=config)   # resume from interrupt

    wf.status = graph.get_state(config).values["status"]
    wf.decided_at = datetime.utcnow()
    db.commit(); db.refresh(wf)
    return WorkflowOut.model_validate(wf)


@router.post("/workflows/{workflow_id}/approve", response_model=WorkflowOut)
@limiter.limit("10/minute")
def approve_workflow(
    request: Request,
    workflow_id: UUID,
    db: Session = Depends(get_db),
):
    return _decide(workflow_id, "approve", db)


@router.post("/workflows/{workflow_id}/reject", response_model=WorkflowOut)
@limiter.limit("10/minute")
def reject_workflow(
    request: Request,
    workflow_id: UUID,
    db: Session = Depends(get_db),
):
    return _decide(workflow_id, "reject", db)
