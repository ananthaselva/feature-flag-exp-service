from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

# Import require_auth for JWT validation
from app.deps import require_tenant, require_auth, get_db
from app.models import Flag
from app.schemas import FlagIn, FlagOut
from app.services.audit import record_audit
from app.services.cache import invalidate_flag_cache

router = APIRouter(prefix="/v1/flags", tags=["flags"])


@router.post("", response_model=FlagOut, status_code=status.HTTP_201_CREATED)
async def create_flag(
    flag_in: FlagIn,
    tenant: str = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Idempotent create:
    - If the flag exists (same tenant + key and not soft-deleted), return 200 with existing.
    - Otherwise create and return 201.
    """
    q = select(Flag).where(
        Flag.tenant_id == tenant,
        Flag.key == flag_in.key,
        Flag.deleted_at.is_(None),
    )
    res = await db.execute(q)
    existing = res.scalars().first()
    if existing:
        return JSONResponse(
            content=jsonable_encoder(existing, by_alias=True),
            status_code=status.HTTP_200_OK,
        )

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
            return JSONResponse(
                content=jsonable_encoder(existing, by_alias=True),
                status_code=status.HTTP_200_OK,
            )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict creating flag")

    await db.refresh(new_flag)

    # Audit logging
    actor = "system"  # replace with JWT sub when auth is implemented
    await record_audit(
        db=db,
        tenant=tenant,
        actor=actor,
        entity="flag",
        entity_key=new_flag.key,
        action="create",
        before=None,
        after={
            "key": new_flag.key,
            "description": new_flag.description,
            "state": new_flag.state,
            "variants": new_flag.variants,
            "rules": new_flag.rules,
        },
    )

    # Cache invalidation
    try:
        invalidate_flag_cache(tenant, new_flag.key)
    except Exception:
        pass

    return JSONResponse(
        content=jsonable_encoder(new_flag, by_alias=True),
        status_code=status.HTTP_201_CREATED,
    )


@router.get("", response_model=List[FlagOut], dependencies=[Depends(require_auth)])
async def list_flags(
    tenant: str = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
    state: Optional[str] = None,
    q: Optional[str] = None,
):
    """
    Retrieve a list of feature flags for a given tenant.

    Supports:
    1. Pagination:
       - `limit`: maximum number of flags to return (default 100)
       - `offset`: number of flags to skip (for paging)
    2. Filtering:
       - `state`: filter flags by state (e.g., 'on' or 'off')
       - `q`: search for flags by partial key match
    3. Excludes soft-deleted flags automatically.

    Returns:
        List[FlagOut]: A list of flag objects matching the criteria.
    """
    query = select(Flag).where(Flag.tenant_id == tenant, Flag.deleted_at.is_(None))

    if state:
        query = query.where(Flag.state == state)
    if q:
        query = query.where(Flag.key.ilike(f"%{q}%"))

    query = query.offset(offset).limit(limit)
    res = await db.execute(query)
    return res.scalars().all()


@router.get("/{key}", response_model=FlagOut, dependencies=[Depends(require_auth)])
async def get_flag(key: str, tenant: str = Depends(require_tenant), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Flag).where(Flag.tenant_id == tenant, Flag.key == key, Flag.deleted_at.is_(None))
    )
    flag = res.scalars().first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")
    return flag


@router.put("/{key}", response_model=FlagOut)
async def update_flag(key: str, flag_in: FlagIn, tenant: str = Depends(require_tenant), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Flag).where(Flag.tenant_id == tenant, Flag.key == key, Flag.deleted_at.is_(None))
    )
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

    # Audit
    actor = "system"
    await record_audit(db, tenant, actor, "flag", key, "update", before, jsonable_encoder(flag, by_alias=True))

    # Cache bust
    try:
        invalidate_flag_cache(tenant, key)
    except Exception:
        pass

    return flag


@router.delete("/{key}", status_code=204)
async def delete_flag(
    key: str,
    tenant: str = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-delete a flag:
    - Marks deleted_at timestamp
    - Logs audit
    - Busts cache
    """
    # Fetch the existing flag (skip already deleted)
    res = await db.execute(
        select(Flag).where(Flag.tenant_id == tenant, Flag.key == key, Flag.deleted_at.is_(None))
    )
    flag = res.scalars().first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    # Capture "before" state for audit
    before = jsonable_encoder(flag, by_alias=True)

    # Perform soft delete
    flag.deleted_at = datetime.utcnow()
    db.add(flag)
    await db.commit()

    # Record audit event
    actor = "system"  # replace with JWT subject if available
    await record_audit(db, tenant, actor, "flag", key, "delete", before, None)

    # Invalidate cache
    try:
        invalidate_flag_cache(tenant, key)
    except Exception:
        # Silent fail; log in production if needed
        pass