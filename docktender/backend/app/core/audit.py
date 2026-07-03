"""Audit-log helper. Call on every mutation to tenant-scoped entities."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import AuditLog


def audit(
    db: Session,
    *,
    org_id: str,
    actor_id: str | None,
    action: str,
    entity: str,
    entity_id: str = "",
    detail: dict | None = None,
) -> AuditLog:
    row = AuditLog(
        org_id=org_id,
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        detail_json=detail or {},
    )
    db.add(row)
    return row
