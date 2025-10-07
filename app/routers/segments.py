from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import require_tenant
from app.schemas import SegmentIn, SegmentOut

router = APIRouter(prefix="/v1/segments", tags=["segments"])


@router.post("", response_model=SegmentOut, status_code=status.HTTP_201_CREATED)
async def create_segment(_: SegmentIn, tenant: str = Depends(require_tenant)):
    # TODO (candidate):
    # - Idempotent create by (tenant, key)
    # - Persist criteria (JSON) and timestamps
    # - Record audit entry; invalidate any segment caches
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("", response_model=List[SegmentOut])
async def list_segments(tenant: str = Depends(require_tenant)):
    # TODO (candidate): Pagination + optional filters
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{key}", response_model=SegmentOut)
async def get_segment(key: str, tenant: str = Depends(require_tenant)):
    # TODO (candidate): Fetch by (tenant, key); 404 when missing
    raise HTTPException(status_code=501, detail="Not implemented")


@router.put("/{key}", response_model=SegmentOut)
async def update_segment(key: str, _: SegmentIn, tenant: str = Depends(require_tenant)):
    # TODO (candidate): Update criteria; audit before/after; cache-bust
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{key}", status_code=204)
async def delete_segment(key: str, tenant: str = Depends(require_tenant)):
    # TODO (candidate): Soft-delete or hard-delete; audit; cache-bust
    raise HTTPException(status_code=501, detail="Not implemented")
