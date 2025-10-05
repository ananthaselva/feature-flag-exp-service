from fastapi import APIRouter

from app.config import settings
from app.schemas import TokenRequest, TokenResponse
from app.utils.security import issue_token

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def token(body: TokenRequest):
    # Stubbed token issuer so candidates can test flows;
    # enforcement happens in deps.require_auth (TODO).
    tok = issue_token(settings.jwt_secret, body.client_id, body.scopes)
    return TokenResponse(access_token=tok)
