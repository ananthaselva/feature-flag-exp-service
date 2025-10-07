# security.py
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from jose import JWTError, ExpiredSignatureError, jwt
from app.config import settings

ALGO = "HS256"


def issue_token(client_id: str, scopes: list[str]) -> str:
    """
    Generate JWT for a client or testing.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": client_id,
        "scopes": scopes,
        "iat": now.timestamp(),
        "exp": (
            now + timedelta(hours=getattr(settings, "jwt_exp_hours", 12))
        ).timestamp(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def verify_token(token: str) -> dict:
    """
    Verify JWT token and return decoded payload.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
