from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "ok"


@router.get("/readyz", response_class=PlainTextResponse)
async def readyz():
    return "ready"
