# app/routers/auth.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.utils.security import issue_token, verify_token

router = APIRouter(prefix="/v1/auth", tags=["auth"])


# -------------------------
# Request/Response schemas
# -------------------------
class TokenRequest(BaseModel):
    client_id: str
    scopes: List[str]


class TokenResponse(BaseModel):
    token: str


class VerifyRequest(BaseModel):
    token: str


class VerifyResponse(BaseModel):
    sub: str
    scopes: List[str]
    iat: float
    exp: float


# -------------------------
# Issue JWT token
# -------------------------
@router.post("/token", response_model=TokenResponse)
async def get_token(body: TokenRequest):
    token = issue_token(body.client_id, body.scopes)
    return {"token": token}


# -------------------------
# Verify JWT token
# -------------------------
@router.post("/verify", response_model=VerifyResponse)
async def verify_token_endpoint(body: VerifyRequest):
    payload = verify_token(body.token)
    return VerifyResponse(**payload)
