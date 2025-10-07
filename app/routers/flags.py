# app/routers/flags.py
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi import Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.deps import get_db, require_auth
from app.models import Flag
from app.schemas import FlagIn, FlagOut
from app.services.audit import record_audit
from app.services.cache import invalidate_flag_cache

router = APIRouter(prefix="/v1/flags", tags=["flags"])


# -------------------------
# CREATE FLAG
# -------------------------
@router.post("", response_model=FlagOut, status_code=status.HTTP_201_CREATED)
async def create_flag(
    flag_in: FlagIn,
    request: Request,
    payload: dict = Depends(lambda r=Depends(require_auth): require_auth(r, required_scope="flags:rw")),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant
    user = request.state.user

    q = select(Flag).where(Flag.tenant_id == tenant, Flag.key == flag_in.key, Flag.deleted_at.is_(None))
    res = await db.execute(q)
    existing: Optional[Flag] = res.scalars().first()
    if existing:
        return JSONResponse(content=jsonable_encoder(existing, by_alias=True), status_code=status.HTTP_200_OK)

    # Ensure rules and variants are always lists
    rules: List[Dict[str, Any]] = []
    for r in flag_in.rules or []:
        rollout_dict: Optional[Dict[str, Any]] = None
        if r.rollout:
            rollout_dict = {
                **r.rollout.__dict__,
                "distribution": [d.__dict__ for d in r.rollout.distribution or []]
            }
        rule_dict = {**r.__dict__, "rollout": rollout_dict}
        rules.append(rule_dict)

    variants: List[Dict[str, Any]] = [v.__dict__ for v in flag_in.variants or []]

    new_flag = Flag(
        tenant_id=tenant,
        key=flag_in.key,
        description=flag_in.description,
        state=flag_in.state,
        variants=variants,
        rules=rules,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_flag)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        res = await db.execute(q)
        existing = res.scalars().first()
        if existing:
            return JSONResponse(content=jsonable_encoder(existing, by_alias=True), status_code=status.HTTP_200_OK)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict creating flag")

    await db.refresh(new_flag)

    await record_audit(db, tenant, user, "flag", new_flag.key, "create", before=None, after=jsonable_encoder(new_flag, by_alias=True))
    try:
        invalidate_flag_cache(tenant, new_flag.key)
    except Exception:
        pass

    return JSONResponse(content=jsonable_encoder(new_flag, by_alias=True), status_code=status.HTTP_201_CREATED)


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

    q = select(Flag).where(Flag.tenant_id == tenant, Flag.key == flag_key, Flag.deleted_at.is_(None))
    res = await db.execute(q)
    existing: Optional[Flag] = res.scalars().first()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    rules: List[Dict[str, Any]] = []
    for r in flag_in.rules or []:
        rollout_dict: Optional[Dict[str, Any]] = None
        if r.rollout:
            rollout_dict = {
                **r.rollout.__dict__,
                "distribution": [d.__dict__ for d in r.rollout.distribution or []]
            }
        rule_dict = {**r.__dict__, "rollout": rollout_dict}
        rules.append(rule_dict)

    variants: List[Dict[str, Any]] = [v.__dict__ for v in flag_in.variants or []]

    existing.description = flag_in.description
    existing.state = flag_in.state
    existing.rules = rules
    existing.variants = variants
    existing.updated_at = datetime.utcnow()

    db.add(existing)
    await db.commit()
    await db.refresh(existing)

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

    q = select(Flag).where(Flag.tenant_id == tenant, Flag.key == flag_key, Flag.deleted_at.is_(None))
    res = await db.execute(q)
    existing = res.scalars().first()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    existing.deleted_at = datetime.utcnow()
    db.add(existing)
    await db.commit()

    # Audit + cache
    await record_audit(db, tenant, user, "flag", flag_key, "delete", before=jsonable_encoder(existing, by_alias=True), after=None)
    try:
        invalidate_flag_cache(tenant, flag_key)
    except Exception:
        pass

    #return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)
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

    q = select(Flag).where(Flag.tenant_id == tenant, Flag.key == flag_key, Flag.deleted_at.is_(None))
    res = await db.execute(q)
    existing = res.scalars().first()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    return JSONResponse(content=jsonable_encoder(existing, by_alias=True), status_code=status.HTTP_200_OK)