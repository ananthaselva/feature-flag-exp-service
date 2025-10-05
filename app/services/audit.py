# app/services/audit.py
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Audit


async def record_audit(
    db: AsyncSession,
    tenant: str,
    actor: str,
    entity: str,
    entity_key: str,
    action: str,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
) -> Audit:

    #Persist an audit entry.
    
    entry = Audit(
        tenant_id=tenant,
        actor=actor,
        entity=entity,
        entity_key=entity_key,
        action=action,
        before=before,
        after=after,
        ts=datetime.utcnow(),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_audit(
    db: AsyncSession,
    tenant: str,
    *,
    entity: Optional[str] = None,
    entity_key: Optional[str] = None,
    limit: int = 100,
) -> List[Audit]:
    """
    Query audit log for a tenant with optional filters.
    Returns most recent first.
    """
    q = select(Audit).where(Audit.tenant_id == tenant)

    if entity:
        q = q.where(Audit.entity == entity)
    if entity_key:
        q = q.where(Audit.entity_key == entity_key)

    q = q.order_by(desc(Audit.ts)).limit(limit)

    res = await db.execute(q)
    return res.scalars().all()
