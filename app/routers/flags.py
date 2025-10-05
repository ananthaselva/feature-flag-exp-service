from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import require_tenant
from app.schemas import FlagIn, FlagOut

router = APIRouter(prefix="/v1/flags", tags=["flags"])


@router.post("", response_model=FlagOut, status_code=status.HTTP_201_CREATED)
async def create_flag(_: FlagIn, tenant: str = Depends(require_tenant)):
    # TODO: implement idempotent create (tenant+key), persist, audit, cache bust
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("", response_model=List[FlagOut])
async def list_flags(tenant: str = Depends(require_tenant)):
    # TODO: pagination & filters
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{key}", response_model=FlagOut)
async def get_flag(key: str, tenant: str = Depends(require_tenant)):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.put("/{key}", response_model=FlagOut)
async def update_flag(key: str, _: FlagIn, tenant: str = Depends(require_tenant)):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{key}", status_code=204)
async def delete_flag(key: str, tenant: str = Depends(require_tenant)):
    raise HTTPException(status_code=501, detail="Not implemented")
