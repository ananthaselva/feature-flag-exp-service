# deps.py
from typing import Annotated, AsyncGenerator
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text
from app.config import settings
from app.utils.security import verify_token

# -------------------------
# Database setup
# -------------------------
engine = create_async_engine(settings.db_dsn, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


# -------------------------
# Tenant extraction
# -------------------------
Tenant = Annotated[str, Header(alias="X-Tenant-ID")]


async def require_tenant(
    tenant: Tenant,
    db: AsyncSession = Depends(get_db),
) -> str:
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header required",
        )

    # Check if tenant exists in DB (flags or segments)
    result = await db.execute(
        text("""
            SELECT 1 FROM flags WHERE tenant_id = :tenant
            UNION
            SELECT 1 FROM segments WHERE tenant_id = :tenant
            LIMIT 1
        """),
        {"tenant": tenant},
    )
    if not result.first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant '{tenant}' not recognized",
        )

    return tenant


# -------------------------
# JWT + tenant enforcement
# -------------------------
async def require_auth(
    request: Request,
    tenant: str = Depends(require_tenant),
    required_scope: str | None = None,
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.split(" ", 1)[1]
    payload = verify_token(token)

    if required_scope and required_scope not in payload.get("scopes", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required scope: {required_scope}",
        )

    # Attach to request.state
    request.state.user = payload.get("sub")
    request.state.scopes = payload.get("scopes", [])
    request.state.tenant = tenant

    return payload