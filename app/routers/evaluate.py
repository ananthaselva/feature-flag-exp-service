from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from app.deps import get_db, require_tenant
from app.models import Flag
from app.schemas import EvaluateRequest, EvaluateResponse
from app.services.cache import TTLCache
from app.services.flag_eval import evaluate_flag

router = APIRouter(prefix="/v1", tags=["evaluate"])

flag_cache = TTLCache(ttl_seconds=15)
FLAG_CACHE_PREFIX = "flag:"


def get_flag_cache_key(tenant: str, flag_key: str) -> str:
    return f"{FLAG_CACHE_PREFIX}{tenant}:{flag_key}"


def flag_to_dict(flag: Flag) -> dict[str, Any]:
    # Convert Flag SQLAlchemy object to dict
    return {c.name: getattr(flag, c.name) for c in flag.__table__.columns}


@router.post(
    "/evaluate", response_model=EvaluateResponse, status_code=status.HTTP_200_OK
)
async def evaluate(
    body: EvaluateRequest, tenant: str = Depends(require_tenant), db: AsyncSession = Depends(get_db)
):
    cache_key = get_flag_cache_key(tenant, body.flag_key)

    # Check cache first
    flag_data = flag_cache.get(cache_key)

    if not flag_data:
        # Query DB using the column names
        stmt = select(Flag).where(Flag.key == body.flag_key, Flag.tenant_id == tenant)
        flag_obj = (await db.execute(stmt)).scalar_one_or_none()

        if not flag_obj:
            raise HTTPException(status_code=404, detail="Flag not found")

        flag_data = flag_to_dict(flag_obj)
        flag_cache.set(cache_key, flag_data)

    # Evaluate flag
    result = evaluate_flag(flag_data, tenant, body.user)

    # Ensure variant/reason are strings
    variant = result.get("variant") or "none"
    reason = result.get("reason") or "unknown"

    return EvaluateResponse(
        variant=variant,
        reason=reason,
        rule_id=result.get("rule_id"),
        details=result.get("details") or {},
    )
