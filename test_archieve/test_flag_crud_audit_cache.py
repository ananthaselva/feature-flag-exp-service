# tests/test_flag_crud_audit_cache.py
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.flags import create_flag
from app.schemas import FlagIn
from app.deps import SessionLocal
from app.services.audit import list_audit
from app.services.cache import TTLCache

# Test data
TENANT_ID = "ABC"
FLAG_PAYLOAD = FlagIn(
    key="featureabcd",
    description="testfeature20",
    state="on",
    variants=[{"key": "string", "weight": 100}],
    rules=[],
)

# In-memory cache for testing
cache = TTLCache()

async def test_flag_crud_audit_cache():
    async with SessionLocal() as db:
        # Create flag
        response = await create_flag(flag_in=FLAG_PAYLOAD, tenant=TENANT_ID, db=db)
        print("Create Flag Response:", response.body.decode() if hasattr(response, "body") else response)

        # Idempotent create (calling create again)
        response2 = await create_flag(flag_in=FLAG_PAYLOAD, tenant=TENANT_ID, db=db)
        assert response2.status_code in (200, 201)
        print("Idempotent create returned status:", response2.status_code)
        print("Idempotent create returned response:", response.body.decode() if hasattr(response, "body") else response)

        # Cache set and invalidate
        cache_key = f"{TENANT_ID}:{FLAG_PAYLOAD.key}"
        cache.set(cache_key, "cached_value")
        cache.invalidate_prefix(f"{TENANT_ID}:")
        assert cache.get(cache_key) is None
        print("Cache invalidation works for key:", cache_key)

        # Check audit entry exists
        audit_entries = await list_audit(db=db, tenant=TENANT_ID, limit=10)
        assert any(entry.entity_key == FLAG_PAYLOAD.key for entry in audit_entries), "Audit not recorded"
        print("Audit entry recorded for flag:", FLAG_PAYLOAD.key)

if __name__ == "__main__":
    asyncio.run(test_flag_crud_audit_cache())