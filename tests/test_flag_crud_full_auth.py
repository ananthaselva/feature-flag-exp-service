# tests/test_flag_crud_full_auth.py
import pytest
from httpx import AsyncClient
from app.main import app
from app.schemas import FlagIn
from app.services.audit import list_audit
from app.services.cache import TTLCache
from app.deps import SessionLocal

TENANT_ID = "ABC"
FLAG_KEY = "feature31"
CACHE = TTLCache()  # in-memory test cache

@pytest.mark.asyncio
async def test_flag_crud_simple():
    headers = {"X-Tenant-ID": TENANT_ID}  # simple tenant auth header

    flag_payload = FlagIn(
        key=FLAG_KEY,
        description="Integration test feature",
        state="on",
        variants=[{"key": "v1", "weight": 100}],
        rules=[],
    )

    async with AsyncClient(app=app, base_url="http://test") as client:
        # create flag
        response = await client.post("/v1/flags", json=flag_payload.dict(), headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["key"] == FLAG_KEY
        assert data["state"] == "on"

        # create again (idempotent)
        response2 = await client.post("/v1/flags", json=flag_payload.dict(), headers=headers)
        assert response2.status_code == 200

        # update flag
        updated_payload = flag_payload.copy()
        updated_payload.description = "Updated description"
        updated_payload.state = "off"
        response3 = await client.put(f"/v1/flags/{FLAG_KEY}", json=updated_payload.dict(), headers=headers)
        assert response3.status_code == 200
        updated_data = response3.json()
        assert updated_data["description"] == "Updated description"
        assert updated_data["state"] == "off"

        # test cache invalidation
        cache_key = f"{TENANT_ID}:{FLAG_KEY}"
        CACHE.set(cache_key, "cached_value")
        CACHE.invalidate_prefix(f"{TENANT_ID}:")
        assert CACHE.get(cache_key) is None

        # delete flag
        response4 = await client.delete(f"/v1/flags/{FLAG_KEY}", headers=headers)
        assert response4.status_code == 204

        # check audit entries
        async with SessionLocal() as db:
            audits = await list_audit(db=db, tenant=TENANT_ID, limit=20)
            actions = [a.action for a in audits if a.entity_key == FLAG_KEY]
            assert "create" in actions
            assert "update" in actions
            assert "delete" in actions