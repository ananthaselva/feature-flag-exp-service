# app/routers/segments.py

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Request, status, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_auth
from app.models import Segment
from app.schemas import SegmentIn, SegmentOut
from app.services.audit import record_audit
from app.services.cache import invalidate_segment_cache

router = APIRouter(prefix="/v1/segments", tags=["segments"])


@router.post("", response_model=SegmentOut, status_code=status.HTTP_201_CREATED)
async def create_segment(
    segment_in: SegmentIn,
    request: Request,
    payload: dict = Depends(
        lambda r=Depends(require_auth): require_auth(r, required_scope="segments:rw")
    ),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant
    user = request.state.user

    # Idempotent create by (tenant, key)
    q = select(Segment).where(
        Segment.tenant_id == tenant, Segment.key == segment_in.key
    )
    res = await db.execute(q)
    existing: Optional[Segment] = res.scalars().first()
    if existing:
        return JSONResponse(
            content=jsonable_encoder(existing, by_alias=True),
            status_code=status.HTTP_200_OK,
        )

    # Persist criteria (JSON) and timestamps
    new_segment = Segment(
        tenant_id=tenant,
        key=segment_in.key,
        criteria=segment_in.criteria or {},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_segment)
    try:
        await db.commit()
    except IntegrityError:
        # Retry fetch if conflict detected
        await db.rollback()
        res = await db.execute(q)
        existing = res.scalars().first()
        if existing:
            return JSONResponse(
                content=jsonable_encoder(existing, by_alias=True),
                status_code=status.HTTP_200_OK,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Conflict creating segment"
        )

    await db.refresh(new_segment)

    # Record audit entry; invalidate any segment caches
    await record_audit(
        db,
        tenant,
        user,
        "segment",
        new_segment.key,
        "create",
        before=None,
        after=jsonable_encoder(new_segment, by_alias=True),
    )

    try:
        invalidate_segment_cache(tenant, new_segment.key)
    except Exception:
        pass

    return JSONResponse(
        content=jsonable_encoder(new_segment, by_alias=True),
        status_code=status.HTTP_201_CREATED,
    )


@router.get("", response_model=List[SegmentOut])
async def list_segments(
    request: Request,
    payload: dict = Depends(
        lambda r=Depends(require_auth): require_auth(r, required_scope="segments:ro")
    ),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant

    # List segments; pagination and filters can be added later
    q = select(Segment).where(Segment.tenant_id == tenant)
    res = await db.execute(q)
    segments = res.scalars().all()
    return segments


@router.get("/{key}", response_model=SegmentOut)
async def get_segment(
    key: str,
    request: Request,
    payload: dict = Depends(
        lambda r=Depends(require_auth): require_auth(r, required_scope="segments:ro")
    ),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant

    # Fetch by (tenant, key); return 404 when missing
    q = select(Segment).where(Segment.tenant_id == tenant, Segment.key == key)
    res = await db.execute(q)
    segment = res.scalars().first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    return JSONResponse(
        content=jsonable_encoder(segment, by_alias=True),
        status_code=status.HTTP_200_OK,
    )


@router.put("/{key}", response_model=SegmentOut)
async def update_segment(
    key: str,
    segment_in: SegmentIn,
    request: Request,
    payload: dict = Depends(
        lambda r=Depends(require_auth): require_auth(r, required_scope="segments:rw")
    ),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant
    user = request.state.user

    # Update criteria; record audit before/after; cache-bust
    q = select(Segment).where(Segment.tenant_id == tenant, Segment.key == key)
    res = await db.execute(q)
    existing = res.scalars().first()
    if not existing:
        raise HTTPException(status_code=404, detail="Segment not found")

    before = jsonable_encoder(existing, by_alias=True)

    existing.criteria = segment_in.criteria or {}
    existing.updated_at = datetime.utcnow()

    db.add(existing)
    await db.commit()
    await db.refresh(existing)

    await record_audit(
        db,
        tenant,
        user,
        "segment",
        key,
        "update",
        before=before,
        after=jsonable_encoder(existing, by_alias=True),
    )

    try:
        invalidate_segment_cache(tenant, key)
    except Exception:
        pass

    return JSONResponse(
        content=jsonable_encoder(existing, by_alias=True),
        status_code=status.HTTP_200_OK,
    )


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment(
    key: str,
    request: Request,
    payload: dict = Depends(
        lambda r=Depends(require_auth): require_auth(r, required_scope="segments:rw")
    ),
    db: AsyncSession = Depends(get_db),
):
    tenant = request.state.tenant
    user = request.state.user

    # Soft-delete or hard-delete; record audit; cache-bust
    q = select(Segment).where(Segment.tenant_id == tenant, Segment.key == key)
    res = await db.execute(q)
    existing = res.scalars().first()
    if not existing:
        raise HTTPException(status_code=404, detail="Segment not found")

    before = jsonable_encoder(existing, by_alias=True)

    await db.delete(existing)
    await db.commit()

    await record_audit(
        db,
        tenant,
        user,
        "segment",
        key,
        "delete",
        before=before,
        after=None,
    )

    try:
        invalidate_segment_cache(tenant, key)
    except Exception:
        pass

    return Response(status_code=status.HTTP_204_NO_CONTENT)
