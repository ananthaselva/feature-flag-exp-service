from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    """Basic health check"""
    return "ok"


@router.get("/readyz", response_class=PlainTextResponse)
async def readyz():
    """Basic Readiness check"""
    return "ready"
