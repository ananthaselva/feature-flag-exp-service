import sys
import os

# Add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import pytest
from fastapi import status
from httpx import AsyncClient

from app.main import app
from app.services.cache import TTLCache, invalidate_flag_cache, get_flag_cache_key
from app.deps import SessionLocal
from app.models import Flag, Audit

TENANT = "my_test_tenant"
FLAG_KEY = "string"

# Simple in-memory cache instance (shared with your app)
flag_cache = TTLCache(ttl_seconds=30)

@pytest.mark.asyncio
async def test_flag_crud_audit_cache():
    async with AsyncClient(app=app, base_url="http://test") as client:

        # --- 1. GET seeded flag ---
        res = await client.get(f"/v1/flags/{FLAG_KEY}", headers={"X-Tenant-ID": TENANT})
        assert res.status_code == status.HTTP_200_OK
        flag_data = res.json()
        assert flag_data["key"] == FLAG_KEY
        print("✅ Seeded flag exists and retrieved successfully.")

        # --- 2. Idempotent create on existing flag ---
        payload = {
            "key": FLAG_KEY,
            "description": "Should not overwrite seeded",
            "state": "off",
            "variants": [],
            "rules": []
        }
        res2 = await client.post("/v1/flags", json=payload, headers={"X-Tenant-ID": TENANT})
        assert res2.status_code == status.HTTP_200_OK
        data2 = res2.json()
        assert data2["key"] == FLAG_KEY
        print("✅ Idempotent create returned existing seeded flag.")

        # --- 3. Audit check ---
        res3 = await client.get("/v1/audit", headers={"X-Tenant-ID": TENANT})
        assert res3.status_code == status.HTTP_200_OK
        audit_entries = res3.json()
        assert any(entry["entity_key"] == FLAG_KEY for entry in audit_entries)
        print("✅ Audit entries exist for seeded flag.")

        # --- 4. Cache invalidation ---
        cache_key = get_flag_cache_key(TENANT, FLAG_KEY)
        flag_cache.set(cache_key, {"dummy": True})
        assert flag_cache.get(cache_key) is not None
        invalidate_flag_cache(TENANT, FLAG_KEY)
        assert flag_cache.get(cache_key) is None
        print("✅ Cache invalidation works for seeded flag.")


if __name__ == "__main__":
    asyncio.run(test_flag_crud_audit_cache())