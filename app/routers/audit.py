from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_tenant
from app.services.audit import list_audit

router = APIRouter(prefix="/v1/audit", tags=["audit"])


@router.get("")
async def list_audit_entries(tenant: str = Depends(require_tenant)):
    # TODO (candidate):
    # - Query audit entries by tenant with optional filters (entity, entity_key, time window)
    # - Return in reverse chronological order
    raise HTTPException(status_code=501, detail="Not implemented")
