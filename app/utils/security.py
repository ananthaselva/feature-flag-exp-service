# security.py
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from jose import JWTError, jwt
from app.config import settings

ALGO = "HS256"


def issue_token(client_id: str, scopes: list[str]) -> str:
    """
    Generate JWT for a client or testing.
      - sub: client identifier
      - scopes: permissions
      - iat: issued at
      - exp: expiry in UTC
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": client_id,
        "scopes": scopes,
        "iat": now.timestamp(),
        "exp": (now + timedelta(hours=settings.jwt_exp_hours)).timestamp(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def verify_token(token: str) -> dict:
    """
    Verify JWT token and return decoded payload.
    Error handling:
      - Expired token → 401
      - Malformed token → 401
      - Invalid signature → 401
    """
    try:
        # Decode JWT, verify signature and expiry
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
        return payload
    except jwt.ExpiredSignatureError:
        # Token expired
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except JWTError:
        # Any other JWT decoding/signature error
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )