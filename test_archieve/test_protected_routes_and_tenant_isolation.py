# tests/test_protected_routes_and_tenant_isolation.py
import pytest
from httpx import AsyncClient
from app.main import app
from app.schemas import FlagIn
from app.routers import flags

TENANT_ID = "ABC"
OTHER_TENANT_ID = "XYZ"
FLAG_KEY = "test-flag"

# -------------------------
# Fake dependencies
# -------------------------
def fake_require_flags_write(request):
    request.state.tenant = request.headers.get("X-Tenant-ID", TENANT_ID)
    request.state.user = "test-user"
    return {"sub": request.state.user, "scopes": ["flags:write"]}

def fake_require_flags_read(request):
    request.state.tenant = request.headers.get("X-Tenant-ID", TENANT_ID)
    request.state.user = "test-user"
    return {"sub": request.state.user, "scopes": ["flags:read"]}

# -------------------------
# Override dependencies
# -------------------------
app.dependency_overrides[flags.require_flags_write] = fake_require_flags_write
app.dependency_overrides[flags.require_flags_read] = fake_require_flags_read

# -------------------------
# Test
# -------------------------
@pytest.mark.asyncio
async def test_protected_routes_tenant_isolation():
    flag_payload = FlagIn(
        key=FLAG_KEY,
        description="Tenant isolation test",
        state="on",
        variants=[{"key": "v1", "weight": 100}],
        rules=[{"id": "rule1", "order": 0, "when": {}, "rollout": {"variant": "v1", "weight": 100}}],
    ).model_dump()

    async with AsyncClient(app=app, base_url="http://test") as client:
        test_cases_post = [
            ("Missing JWT", {"X-Tenant-ID": TENANT_ID}),
            ("Invalid JWT", {"X-Tenant-ID": TENANT_ID, "Authorization": "Bearer invalid"}),
            ("Valid JWT", {"X-Tenant-ID": TENANT_ID, "Authorization": "Bearer valid"}),
            ("Cross-tenant", {"X-Tenant-ID": OTHER_TENANT_ID, "Authorization": "Bearer valid"}),
            ("Missing X-Tenant-ID", {"Authorization": "Bearer valid"}),
        ]

        for desc, headers in test_cases_post:
            resp = await client.post("/v1/flags", json=flag_payload, headers=headers)
            print(f"\n--- {desc} ---")
            print("Status:", resp.status_code)
            try:
                print("Response:", resp.json())
            except Exception:
                print("Response Text:", resp.text)
