from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_tenant
from app.models import Audit

router = APIRouter(prefix="/v1/audit", tags=["audit"])


from datetime import datetime
from typing import List
from fastapi import APIRouter, Header, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models import Audit

from app.schemas import AuditOut


router = APIRouter(prefix="/v1/audit", tags=["audit"])

   
@router.get("", response_model=List[AuditOut])
async def list_audit_entries(
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    entity: str | None = Query(None),
    entity_key: str | None = Query(None),
    start_ts: datetime | None = Query(None),
    end_ts: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):

    """
    List audit entries for a tenant with optional filters:
    - entity
    - entity_key
    - start_ts / end_ts
    Returns reverse chronological order, limited by `limit`.
    """
    q = select(Audit).where(Audit.tenant_id == x_tenant_id)
    if entity:
        q = q.where(Audit.entity == entity)
    if entity_key:
        q = q.where(Audit.entity_key == entity_key)
    if start_ts:
        q = q.where(Audit.ts >= start_ts)
    if end_ts:
        q = q.where(Audit.ts <= end_ts)

    q = q.order_by(Audit.ts.desc()).limit(limit)

    res = await db.execute(q)
    entries = res.scalars().all()

    return [AuditOut.from_orm(e) for e in entries]

