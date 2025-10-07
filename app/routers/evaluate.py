from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_tenant
from app.models import Flag
from app.schemas import EvaluateRequest, EvaluateResponse
from app.services.cache import TTLCache
from app.services.flag_eval import evaluate_flag

router = APIRouter(prefix="/v1", tags=["evaluate"])
cache = TTLCache(ttl_seconds=15)


@router.post(
    "/evaluate", response_model=EvaluateResponse, status_code=status.HTTP_200_OK
)
async def evaluate(body: EvaluateRequest, tenant: str = Depends(require_tenant), db: AsyncSession = Depends(get_db)):
    """
    Evaluate a feature flag for a given tenant and user.
    Uses in-memory TTL cache and app.services.flag_eval for evaluation.
    """
    flag_key = body.flag_key
    cache_key = f"flag:{tenant}:{flag_key}"

    # Check in-memory cache first
    cached_variant = cache.get(cache_key)
    if cached_variant is not None:
        return EvaluateResponse(
            variant=cached_variant,
            reason="cache_hit"
        )

    # Load flag from DB
    result = await db.execute(
        select(Flag).where(Flag.tenant == tenant, Flag.key == flag_key)
    )
    flag: Flag | None = result.scalar_one_or_none()

    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag '{flag_key}' not found for tenant '{tenant}'"
        )

    # Evaluate flag using flag_eval
    eval_result = evaluate_flag(flag.dict(), tenant, body.user)

    variant = eval_result.get("variant")

    # Store in cache if variant exists
    if variant is not None:
        cache.set(cache_key, variant)

    return EvaluateResponse(
        variant=variant,
        reason=eval_result.get("reason", ""),
        rule_id=eval_result.get("rule_id"),
        details=eval_result.get("details")
    )


