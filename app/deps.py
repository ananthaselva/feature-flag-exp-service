# deps.py
from typing import Annotated, AsyncGenerator
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text
from app.config import settings
from app.utils.security import verify_token

# -------------------------------------------------------------------
# Database setup
# -------------------------------------------------------------------
engine = create_async_engine(settings.db_dsn, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async SQLAlchemy session.
    Ensures session is properly closed after use.
    """
    async with SessionLocal() as session:
        yield session


# -------------------------------------------------------------------
# Tenant extraction and validation
# -------------------------------------------------------------------
Tenant = Annotated[str, Header(alias="X-Tenant-ID", description="Tenant identifier")]


async def require_tenant(
    tenant: Tenant,
    db: AsyncSession = Depends(get_db)
) -> str:
    """
    Validate tenant header dynamically using DB data.
    - Missing tenant → 400
    - Unknown tenant (no rows found in any table) → 403
    """
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header required",
        )

    # Check if tenant_id exists in DB (Flags or Segments table)
    result = await db.execute(
        text("""
            SELECT 1
            FROM flags
            WHERE tenant_id = :tenant
            UNION
            SELECT 1
            FROM segments
            WHERE tenant_id = :tenant
            LIMIT 1
        """),
        {"tenant": tenant},
    )

    exists = result.first()
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant '{tenant}' not recognized or inactive",
        )

    return tenant


# -------------------------------------------------------------------
# JWT enforcement + tenant isolation
# -------------------------------------------------------------------
async def require_auth(
    request: Request,
    tenant: str = Depends(require_tenant),   # Enforces tenant isolation dynamically
    required_scope: str | None = None
):
    """
    Enforce Authorization: Bearer <JWT> + Tenant isolation.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.split(" ", 1)[1]
    payload = verify_token(token)

    # Optional: enforce required scope
    if required_scope and required_scope not in payload.get("scopes", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required scope: {required_scope}",
        )

    # Attach user info for downstream usage
    request.state.user = payload.get("sub")
    request.state.scopes = payload.get("scopes", [])
    request.state.tenant = tenant

    return payload