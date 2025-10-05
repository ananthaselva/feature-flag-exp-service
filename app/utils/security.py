from datetime import datetime, timedelta

from fastapi import HTTPException, status
from jose import JWTError, jwt

ALGO = "HS256"


def issue_token(secret: str, client_id: str, scopes: list[str]) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": client_id,
        "scopes": scopes,
        "iat": now.timestamp(),
        "exp": (now + timedelta(hours=6)).timestamp(),
    }
    return jwt.encode(payload, secret, algorithm=ALGO)


def verify_token(secret: str, token: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=[ALGO])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
