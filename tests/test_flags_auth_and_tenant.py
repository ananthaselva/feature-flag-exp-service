# tests/test_flags_auth_and_tenant.py
import pytest
from httpx import AsyncClient
from app.main import app
from app.routers import flags
from app.schemas import FlagIn, Variant

TENANT_ID = "ABC"


@pytest.mark.asyncio
async def test_flags_crud_and_auth():
    # ------------------------------
    # Fake dependency to bypass auth & set tenant/user
    # ------------------------------
    async def fake_require_flags_write(request):
        request.state.tenant = TENANT_ID
        request.state.user = "test-user"
        return {"scope": "flags:write"}

    async def fake_require_flags_read(request):
        request.state.tenant = TENANT_ID
        request.state.user = "test-user"
        return {"scope": "flags:read"}

    # Override dependencies
    app.dependency_overrides[flags.require_flags_write] = fake_require_flags_write
    app.dependency_overrides[flags.require_flags_read] = fake_require_flags_read

    # ------------------------------
    # Sample payload
    # ------------------------------
    flag_payload = FlagIn(
        key="test_flag",
        description="Integration test flag",
        state="on",
        variants=[Variant(key="v1", weight=100.0)],
        rules=[],
    )

    # ------------------------------
    # Test CREATE
    # ------------------------------
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/v1/flags", json=flag_payload.dict())
        print("Create Flag Response:", resp.status_code, resp.json())
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["key"] == "test_flag"

    # ------------------------------
    # Test LIST
    # ------------------------------
        resp = await client.get("/v1/flags")
        print("List Flags Response:", resp.status_code, resp.json())
        assert resp.status_code == 200
        assert any(f["key"] == "test_flag" for f in resp.json())

    # ------------------------------
    # Test GET FLAG
    # ------------------------------
        resp = await client.get(f"/v1/flags/{flag_payload.key}")
        print("Get Flag Response:", resp.status_code, resp.json())
        assert resp.status_code == 200
        assert resp.json()["key"] == "test_flag"

    # ------------------------------
    # Test UPDATE FLAG
    # ------------------------------
        updated_payload = flag_payload.copy(update={"description": "Updated"})
        resp = await client.put(f"/v1/flags/{flag_payload.key}", json=updated_payload.dict())
        print("Update Flag Response:", resp.status_code, resp.json())
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated"

    # ------------------------------
    # Test DELETE FLAG
    # ------------------------------
        resp = await client.delete(f"/v1/flags/{flag_payload.key}")
        print("Delete Flag Response:", resp.status_code)
        assert resp.status_code == 204

    # Clear overrides
    app.dependency_overrides = {}