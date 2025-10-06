# tests/test_flags_security_and_tenant.py
import pytest
from httpx import AsyncClient
from app.main import app
from app.schemas import FlagIn, Variant, Rollout, Rule

BASE_URL = "/v1/flags"

# Example JWT tokens for testing
VALID_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X2NsaWVudCIsInNjb3BlcyI6WyJmbGFnczpydyJdLCJpYXQiOjE3NTk3MjIwMDUuMDczNzc1LCJleHAiOjE3NTk3NDM2MDUuMDczNzc1fQ.eKYv2bahohB_d2MqD0838yWWRl4SXS9PkcIKjk2fgAE"      # Fake valid token for test override
INVALID_TOKEN = "invalid"
TENANT_ID = "TENANT_A"
OTHER_TENANT_ID = "TENANT_B"
FLAG_KEY = "test-security-flag"

# -------------------------
# Fake dependencies
# -------------------------
def fake_require_auth(request, required_scope=None):
    """
    Fake auth dependency.
    Will fail if token is 'invalid' or missing.
    """
    auth_header = request.headers.get("Authorization")
    tenant = request.headers.get("X-Tenant-ID")
    request.state.tenant = tenant
    request.state.user = "test-user"

    if not auth_header:
        raise Exception("Missing JWT")
    if auth_header == f"Bearer {INVALID_TOKEN}":
        raise Exception("Invalid JWT")
    return {"sub": request.state.user, "scopes": ["flags:rw"]}

# -------------------------
# Override dependencies
# -------------------------
from app.routers import flags
app.dependency_overrides[flags.require_auth] = fake_require_auth

# -------------------------
# Test payload
# -------------------------
flag_payload_model = FlagIn(
    key=FLAG_KEY,
    description="Security & tenant test",
    state="on",
    variants=[Variant(key="control", weight=50), Variant(key="treatment", weight=50)],
    rules=[
        Rule(
            id="r1",
            order=0,
            when={},
            rollout=Rollout(
                variant=None,
                weight=None,
                distribution=[Variant(key="control", weight=50), Variant(key="treatment", weight=50)]
            )
        )
    ]
)
flag_payload = flag_payload_model.model_dump()

# -------------------------
# Security & tenant enforcement tests
# -------------------------
@pytest.mark.asyncio
async def test_security_and_tenant_enforcement():
    async with AsyncClient(app=app, base_url="http://test") as client:
        test_cases = [
            ("Missing JWT", {"X-Tenant-ID": TENANT_ID}, 403),
            ("Invalid JWT", {"Authorization": f"Bearer {INVALID_TOKEN}", "X-Tenant-ID": TENANT_ID}, 403),
            ("Missing X-Tenant-ID", {"Authorization": f"Bearer {VALID_TOKEN}"}, 403),
            ("Valid JWT & tenant", {"Authorization": f"Bearer {VALID_TOKEN}", "X-Tenant-ID": TENANT_ID}, 201),
            ("Cross-tenant write", {"Authorization": f"Bearer {VALID_TOKEN}", "X-Tenant-ID": OTHER_TENANT_ID}, 403),
        ]

        for desc, headers, expected_status in test_cases:
            resp = await client.post(f"{BASE_URL}", json=flag_payload, headers=headers)
            print(f"\n--- {desc} ---")
            print("Status:", resp.status_code)
            try:
                print("Response:", resp.json())
            except Exception:
                print("Response Text:", resp.text)
            assert resp.status_code == expected_status

# -------------------------
# Tenant isolation test
# -------------------------
@pytest.mark.asyncio
async def test_tenant_isolation():
    async with AsyncClient(app=app, base_url="http://test") as client:
        headers_a = {"Authorization": f"Bearer {VALID_TOKEN}", "X-Tenant-ID": TENANT_ID}
        headers_b = {"Authorization": f"Bearer {VALID_TOKEN}", "X-Tenant-ID": OTHER_TENANT_ID}

        # Create a flag in TENANT_A
        resp = await client.post(f"{BASE_URL}", json=flag_payload, headers=headers_a)
        print("\n--- Create in TENANT_A ---")
        print("Status:", resp.status_code)
        print("Response:", resp.json())
        assert resp.status_code in (200, 201)

        # Attempt to read same flag in OTHER_TENANT_B
        resp = await client.get(f"{BASE_URL}/{FLAG_KEY}", headers=headers_b)
        print("\n--- Read in TENANT_B (should fail) ---")
        print("Status:", resp.status_code)
        try:
            print("Response:", resp.json())
        except Exception:
            print("Response Text:", resp.text)
        assert resp.status_code == 404  # Tenant isolation enforced

        # Read in original tenant
        resp = await client.get(f"{BASE_URL}/{FLAG_KEY}", headers=headers_a)
        print("\n--- Read in TENANT_A (should succeed) ---")
        print("Status:", resp.status_code)
        print("Response:", resp.json())
        assert resp.status_code == 200
