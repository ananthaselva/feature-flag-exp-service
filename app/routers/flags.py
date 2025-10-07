# app/routers/flags.py
import logging
from typing import List
from fastapi import APIRouter, Depends, Request, status, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.deps import get_db, require_auth
from app.models import Flag
from app.schemas import FlagIn, FlagOut
from app.services.audit import record_audit
from app.services.cache import invalidate_flag_cache

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/v1/flags", tags=["flags"])

# Fix: define auth_dependency before it's used
async def auth_dependency(request: Request):
    from app.deps import require_auth  # import here to avoid circular issues
    return await require_auth(request, required_scope="flags:rw")

# -------------------------
# CREATE FLAG
# -------------------------
@router.post("", response_model=FlagOut)
async def create_flag(
    flag_in: FlagIn,
    request: Request,
    payload: dict = Depends(auth_dependency),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant
    user = request.state.user

    async def fetch_existing_flag():
        result = await db.execute(
            select(Flag).where(
                Flag.tenant_id == tenant,
                Flag.key == flag_in.key,
                Flag.deleted_at.is_(None)
            ).limit(1)
        )
        return result.scalars().first()

    # Check if flag already exists
    existing = await fetch_existing_flag()
    if existing:
        return JSONResponse(content=jsonable_encoder(existing, by_alias=True), status_code=200)

    # Prepare new flag
    new_flag = Flag(
        tenant_id=tenant,
        key=flag_in.key,
        description=flag_in.description,
        state=flag_in.state,
        variants=[v.__dict__ for v in flag_in.variants],
        rules=[
            {
                **r.__dict__,
                "rollout": {
                    **r.rollout.__dict__,
                    "distribution": [d.__dict__ for d in r.rollout.distribution]
                } if r.rollout else None
            }
            for r in flag_in.rules
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_flag)
    try:
        await db.commit()
        await db.refresh(new_flag)
    except IntegrityError as e:
        logger.error(f"IntegrityError while creating flag '{flag_in.key}' for tenant '{tenant}': {e}")
        await db.rollback()
        existing = await fetch_existing_flag()
        if existing:
            return JSONResponse(content=jsonable_encoder(existing, by_alias=True), status_code=200)
        raise HTTPException(status_code=409, detail="Conflict creating flag")

    await record_audit(db, tenant, user, "flag", new_flag.key, "create", before=None, after=jsonable_encoder(new_flag, by_alias=True))
    try:
        invalidate_flag_cache(tenant, new_flag.key)
    except Exception:
        pass

    return JSONResponse(content=jsonable_encoder(new_flag, by_alias=True), status_code=201)


# -------------------------
# UPDATE FLAG
# -------------------------
@router.put("/{flag_key}", response_model=FlagOut)
async def update_flag(
    flag_key: str,
    flag_in: FlagIn,
    request: Request,
    payload: dict = Depends(lambda r=Depends(require_auth): require_auth(r, required_scope="flags:rw")),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant
    user = request.state.user

    q = select(Flag).where(
        and_(
            Flag.tenant_id == tenant,
            Flag.key == flag_key,
            Flag.deleted_at.is_(None)
        )
    )
    res = await db.execute(q)
    existing = res.scalars().first()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    # Serialize nested objects
    serialized_rules = []
    for r in flag_in.rules:
        rollout_dict = None
        if r.rollout:
            rollout_dict = {
                **r.rollout.__dict__,
                "distribution": [d.__dict__ for d in r.rollout.distribution]
            }
        rule_dict = {**r.__dict__, "rollout": rollout_dict}
        serialized_rules.append(rule_dict)

    # Update fields
    existing.description = flag_in.description
    existing.state = flag_in.state
    existing.variants = [v.__dict__ for v in flag_in.variants]
    existing.rules = serialized_rules
    existing.updated_at = datetime.utcnow()

    db.add(existing)
    await db.commit()
    await db.refresh(existing)

    # Audit + cache
    # Record audit of update and invalidate cache
    await record_audit(db, tenant, user, "flag", flag_key, "update", before=None, after=jsonable_encoder(existing, by_alias=True))
    try:
        invalidate_flag_cache(tenant, existing.key)
    except Exception:
        pass

    return JSONResponse(content=jsonable_encoder(existing, by_alias=True), status_code=status.HTTP_200_OK)


# -------------------------
# DELETE FLAG
# -------------------------
@router.delete("/{flag_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flag(
    flag_key: str,
    request: Request,
    payload: dict = Depends(lambda r=Depends(require_auth): require_auth(r, required_scope="flags:rw")),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant
    user = request.state.user

    q = select(Flag).where(
        and_(
            Flag.tenant_id == tenant,
            Flag.key == flag_key,
            Flag.deleted_at.is_(None)
        )
    )
    res = await db.execute(q)
    existing = res.scalars().first()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    existing.deleted_at = datetime.utcnow()
    db.add(existing)
    await db.commit()

    # Audit + cache
    # Record audit of deletion and invalidate cache
    await record_audit(db, tenant, user, "flag", flag_key, "delete", before=jsonable_encoder(existing, by_alias=True), after=None)
    try:
        invalidate_flag_cache(tenant, flag_key)
    except Exception:
        pass

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -------------------------
# GET FLAG
# -------------------------
@router.get("/{flag_key}", response_model=FlagOut)
async def get_flag(
    flag_key: str,
    request: Request,
    payload: dict = Depends(lambda r=Depends(require_auth): require_auth(r, required_scope="flags:rw")),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant

    q = select(Flag).where(
        and_(
            Flag.tenant_id == tenant,
            Flag.key == flag_key,
            Flag.deleted_at.is_(None)
        )
    )
    res = await db.execute(q)
    existing = res.scalars().first()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    return JSONResponse(content=jsonable_encoder(existing, by_alias=True), status_code=status.HTTP_200_OK)