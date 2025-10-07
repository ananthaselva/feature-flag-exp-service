# app/services/audit.py
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Audit
from app.schemas import AuditOut


def serialize_model(obj: Union[Dict[str, Any], Any]) -> Optional[Dict[str, Any]]:
    """Convert SQLAlchemy object or dict to JSON-serializable dict."""
    if obj is None:
        return None

    if isinstance(obj, dict):
        return {k: v for k, v in obj.items() if not k.startswith('_')}

    if hasattr(obj, '__dict__'):
        # Only include columns, ignore SQLAlchemy internal attributes
        return {k: v for k, v in vars(obj).items() if not k.startswith('_') and not callable(v)}

    return None


async def record_audit(
    db: AsyncSession,
    tenant: str,
    actor: str,
    entity: str,
    entity_key: str,
    action: str,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
) -> AuditOut:
    """Persist an audit entry."""
    entry = Audit(
        tenant_id=tenant,
        actor=actor,
        entity=entity,
        entity_key=entity_key,
        action=action,
        before=serialize_model(before),
        after=serialize_model(after),
        ts=datetime.utcnow(),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return AuditOut.from_orm(entry)


async def list_audit(
    db: AsyncSession,
    tenant: str,
    *,
    entity: Optional[str] = None,
    entity_key: Optional[str] = None,
    limit: int = 100,
) -> List[AuditOut]:
    """Query audit log for a tenant with optional filters. Returns most recent first."""
    query = select(Audit).where(Audit.tenant_id == tenant)

    if entity:
        query = query.where(Audit.entity == entity)
    if entity_key:
        query = query.where(Audit.entity_key == entity_key)

    query = query.order_by(desc(Audit.ts)).limit(limit)

    result = await db.execute(query)
    entries = result.scalars().all()
    return [AuditOut.from_orm(entry) for entry in entries]