import uuid
from datetime import datetime
from typing import Literal, Optional, TypedDict
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from app.db import Base


# ---------- Pydantic schemas ----------

class ActionItem(BaseModel):
    owner: str
    task: str
    due_date: Optional[str] = None
    source_quote: str


class Draft(BaseModel):
    owner: str
    task: str
    message: str


WorkflowStatus = Literal["pending_approval", "sent", "rejected"]


class StartWorkflowRequest(BaseModel):
    meeting_id: UUID
    action_items: list[ActionItem]


class WorkflowOut(BaseModel):
    id: UUID
    meeting_id: UUID
    status: WorkflowStatus
    drafts: list[Draft]
    created_at: datetime
    decided_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class WorkflowListItem(BaseModel):
    id: UUID
    meeting_id: UUID
    status: WorkflowStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- LangGraph state ----------

class WorkflowState(TypedDict, total=False):
    meeting_id: str
    action_items: list[dict]
    drafts: list[dict]
    decision: Optional[str]   # "approve" | "reject" | None
    status: str


# ---------- SQLAlchemy model ----------

class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    status = Column(String, nullable=False, default="drafting")
    drafts = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    decided_at = Column(DateTime, nullable=True)
