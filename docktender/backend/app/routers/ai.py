"""AI assistant endpoint + review-queue decisions."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai import assistant
from ..ai.client import ai_available
from ..db import get_db
from ..deps import get_current_user
from ..models import AgentEvent, User
from ..schemas import ChatIn

router = APIRouter(prefix="/api", tags=["ai"])


@router.post("/ai/chat")
def chat(body: ChatIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if not ai_available():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Assistant unavailable — no API key configured.")
    reply = assistant.chat(db, user, [m.model_dump() for m in body.messages])
    if reply is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Assistant unavailable")
    return {"reply": reply}


@router.get("/agents/events")
def list_events(needs_decision: bool | None = None, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(AgentEvent).where(AgentEvent.org_id == user.org_id).order_by(AgentEvent.ts.desc())
    if needs_decision is not None:
        stmt = stmt.where(AgentEvent.needs_decision == needs_decision)
    return [{
        "id": e.id, "agent": e.agent, "agent_label": e.agent.replace("_", " ").title(),
        "severity": e.severity, "message": e.message, "evidence": e.evidence,
        "needs_decision": e.needs_decision, "decided_by": e.decided_by,
    } for e in db.scalars(stmt)]


@router.patch("/agents/events/{event_id}")
def decide_event(event_id: str, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)) -> dict:
    e = db.get(AgentEvent, event_id)
    if not e or e.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    e.needs_decision = False
    e.decided_by = user.full_name or user.email
    db.commit()
    return {"id": e.id, "needs_decision": e.needs_decision, "decided_by": e.decided_by}
