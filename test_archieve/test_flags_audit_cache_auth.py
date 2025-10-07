# tests/test_flags_audit_cache_auth.py
import pytest
from httpx import AsyncClient

from app.main import app
from app.schemas import FlagIn
from app.services.audit import list_audit
from app.services.cache import TTLCache
from app.deps import get_db
from app.utils.security import issue_token

TENANT_ID = "ABC"
FLAG_KEY = "test1"

cache = TTLCache()


@pytest.mark.asyncio
async def test_flag_crud_with_jwt():
    # -------------------------
    # Prepare JWT
    # -------------------------
    token = issue_token(client_id="test-client", scopes=["flags:write", "flags:read"])
    headers = {"X-Tenant-ID": TENANT_ID, "Authorization": f"Bearer {token}"}

    # -------------------------
    # Get a real AsyncSession from the generator
    # -------------------------
    async for db_session in get_db():
        try:
            # -------------------------
            # Prepare payload
            # -------------------------
            flag_payload = FlagIn(
                key=FLAG_KEY,
                description="Integration test feature",
                state="on",
                variants=[{"key": "v1", "weight": 100}],
                rules=[]
            )

            # -------------------------
            # API calls with JWT
            # -------------------------
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Create flag
                response = await client.post("/v1/flags", json=flag_payload.model_dump(), headers=headers)
                print("Create Flag Response:", response.json())

                # Idempotent create
                response2 = await client.post("/v1/flags", json=flag_payload.model_dump(), headers=headers)
                print("Idempotent Create Response:", response2.json())

            # -------------------------
            # Cache test
            # -------------------------
            cache_key = f"{TENANT_ID}:{FLAG_KEY}"
            cache.set(cache_key, "cached_value")
            print("Cache before invalidation:", cache.get(cache_key))
            cache.invalidate_prefix(f"{TENANT_ID}:")
            print("Cache after invalidation:", cache.get(cache_key))

            # -------------------------
            # Audit check
            # -------------------------
            audit_entries = await list_audit(db=db_session, tenant=TENANT_ID, limit=10)
            print("Recent Audit Entries:")
            for entry in audit_entries:
                print({
                    "entity": entry.entity,
                    "entity_key": entry.entity_key,
                    "tenant_id": entry.tenant_id,
                    "ts": entry.ts.isoformat() if entry.ts else None,
                    "action": entry.action,
                })

            # -------------------------
            # Assertions
            # -------------------------
            assert response.status_code in (200, 201)
            assert response2.status_code in (200, 201)
            assert cache.get(cache_key) is None
            assert any(entry.entity_key == FLAG_KEY for entry in audit_entries)

        finally:
            # Proper cleanup to avoid pending task warnings
            await db_session.rollback()
        break  # only need one session