# tests/test_e2e_tenant_protection.py
import pytest
from httpx import AsyncClient
from app.main import app
from app.schemas import FlagIn
from app.utils.security import issue_token

TENANT_A = "TenantA"
TENANT_B = "TenantB"

@pytest.mark.asyncio
async def test_e2e_tenant_isolation_behavior():
    # Prepare the flag payload
    flag_payload = FlagIn(
        key="tenant_flag",
        description="Tenant isolation test",
        state="on",
        variants=[{"key": "control", "weight": 100}],
        rules=[],
    ).model_dump()

    # Generate a valid JWT for testing
    valid_token = issue_token("test_client", ["flags:write", "flags:read"])

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test cases: missing JWT, invalid JWT, cross-tenant request
        cases = [
            ("Missing JWT", {"X-Tenant-ID": TENANT_A}),
            ("Invalid JWT", {"X-Tenant-ID": TENANT_A, "Authorization": "Bearer invalid"}),
            ("Valid JWT same tenant", {"X-Tenant-ID": TENANT_A, "Authorization": f"Bearer {valid_token}"}),
            ("Valid JWT different tenant", {"X-Tenant-ID": TENANT_B, "Authorization": f"Bearer {valid_token}"}),
        ]

        for desc, headers in cases:
            resp = await client.post("/v1/flags", json=flag_payload, headers=headers)
            print(f"\n--- {desc} ---")
            print("Status:", resp.status_code)
            try:
                print("Response:", resp.json())
            except Exception:
                print("Raw:", resp.text)