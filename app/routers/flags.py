# flags.py
from typing import List, Optional
from fastapi import APIRouter, Depends, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.deps import require_auth, get_db
from app.models import Flag
from app.schemas import FlagIn, FlagOut
from app.services.audit import record_audit
from app.services.cache import invalidate_flag_cache

router = APIRouter(prefix="/v1/flags", tags=["flags"])

# -------------------------
# Dependency wrappers
# -------------------------
def require_flags_write(request: Request):
    return require_auth(request, required_scope="flags:write")

def require_flags_read(request: Request):
    return require_auth(request, required_scope="flags:read")


# -------------------------
# CREATE FLAG
# -------------------------
@router.post("", response_model=FlagOut, status_code=status.HTTP_201_CREATED)
async def create_flag(
    flag_in: FlagIn,
    request: Request,
    payload: dict = Depends(require_flags_write),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant
    user = request.state.user

    # Check if flag exists (idempotent create)
    q = select(Flag).where(Flag.tenant_id == tenant, Flag.key == flag_in.key, Flag.deleted_at.is_(None))
    res = await db.execute(q)
    existing = res.scalars().first()
    if existing:
        return JSONResponse(content=jsonable_encoder(existing, by_alias=True), status_code=status.HTTP_200_OK)

    new_flag = Flag(
        tenant_id=tenant,
        key=flag_in.key,
        description=flag_in.description,
        state=flag_in.state,
        variants=[v.__dict__ if hasattr(v, "__dict__") else v for v in flag_in.variants],
        rules=[r.__dict__ if hasattr(r, "__dict__") else r for r in flag_in.rules],
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

    # Audit & cache
    await record_audit(db, tenant, user, "flag", new_flag.key, "create", before=None, after=jsonable_encoder(new_flag, by_alias=True))
    try:
        invalidate_flag_cache(tenant, new_flag.key)
    except Exception:
        pass

    return JSONResponse(content=jsonable_encoder(new_flag, by_alias=True), status_code=status.HTTP_201_CREATED)


# -------------------------
# LIST FLAGS
# -------------------------
@router.get("", response_model=List[FlagOut])
async def list_flags(
    request: Request,
    payload: dict = Depends(require_flags_read),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
    state: Optional[str] = None,
    q: Optional[str] = None,
):
    tenant = request.state.tenant
    query = select(Flag).where(Flag.tenant_id == tenant, Flag.deleted_at.is_(None))
    if state:
        query = query.where(Flag.state == state)
    if q:
        query = query.where(Flag.key.ilike(f"%{q}%"))

    res = await db.execute(query.offset(offset).limit(limit))
    return res.scalars().all()


# -------------------------
# GET FLAG
# -------------------------
@router.get("/{key}", response_model=FlagOut)
async def get_flag(
    key: str,
    request: Request,
    payload: dict = Depends(require_flags_read),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant
    res = await db.execute(select(Flag).where(Flag.tenant_id == tenant, Flag.key == key, Flag.deleted_at.is_(None)))
    flag = res.scalars().first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")
    return flag


# -------------------------
# UPDATE FLAG
# -------------------------
@router.put("/{key}", response_model=FlagOut)
async def update_flag(
    key: str,
    flag_in: FlagIn,
    request: Request,
    payload: dict = Depends(require_flags_write),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant
    user = request.state.user

    res = await db.execute(select(Flag).where(Flag.tenant_id == tenant, Flag.key == key, Flag.deleted_at.is_(None)))
    flag = res.scalars().first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    before = jsonable_encoder(flag, by_alias=True)
    flag.description = flag_in.description
    flag.state = flag_in.state
    flag.variants = flag_in.variants
    flag.rules = flag_in.rules
    flag.updated_at = datetime.utcnow()

    db.add(flag)
    await db.commit()
    await db.refresh(flag)

    await record_audit(db, tenant, user, "flag", key, "update", before, jsonable_encoder(flag, by_alias=True))
    try:
        invalidate_flag_cache(tenant, key)
    except Exception:
        pass

    return flag


# -------------------------
# DELETE FLAG
# -------------------------
@router.delete("/{key}", status_code=204)
async def delete_flag(
    key: str,
    request: Request,
    payload: dict = Depends(require_flags_write),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant
    user = request.state.user

    res = await db.execute(select(Flag).where(Flag.tenant_id == tenant, Flag.key == key, Flag.deleted_at.is_(None)))
    flag = res.scalars().first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    before = jsonable_encoder(flag, by_alias=True)
    flag.deleted_at = datetime.utcnow()
    db.add(flag)
    await db.commit()

    await record_audit(db, tenant, user, "flag", key, "delete", before, None)
    try:
        invalidate_flag_cache(tenant, key)
    except Exception:
        pass
