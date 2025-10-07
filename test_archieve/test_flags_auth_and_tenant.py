# tests/test_flags_auth_and_tenant.py
import pytest
from httpx import AsyncClient
from app.main import app
from app.deps import require_auth, require_tenant
from app.config import settings

BASE_URL = "/v1/flags"

# Example JWT token for testing
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X2NsaWVudCIsInNjb3BlcyI6WyJmbGFnczpydyJdLCJpYXQiOjE3NTk3MjIwMDUuMDczNzc1LCJleHAiOjE3NTk3NDM2MDUuMDczNzc1fQ.eKYv2bahohB_d2MqD0838yWWRl4SXS9PkcIKjk2fgAE"
TENANT_ID = "acme"

flag_payload = {
    "key": "test3",
    "description": "Test flag description",
    "state": "on",
    "variants": [{"key": "control", "weight": 50}, {"key": "treatment", "weight": 50}],
    "rules": [{"id": "r1", "order": 1, "when": {"percentage": 50}, "rollout": {"distribution":[{"key":"control","weight":50},{"key":"treatment","weight":50}]}}]
}


@pytest.mark.asyncio
async def test_flags_crud():
    async with AsyncClient(app=app, base_url="http://test") as client:
        headers = {
            "Authorization": f"Bearer {TEST_TOKEN}",
            "X-Tenant-ID": TENANT_ID,
        }

        # ---------------------------
        # CREATE FLAG
        # ---------------------------
        resp = await client.post(f"{BASE_URL}", json=flag_payload, headers=headers)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["key"] == flag_payload["key"]

        # ---------------------------
        # GET FLAG
        # ---------------------------
        resp = await client.get(f"{BASE_URL}/{flag_payload['key']}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == flag_payload["key"]

        # ---------------------------
        # UPDATE FLAG
        # ---------------------------
        updated_payload = flag_payload.copy()
        updated_payload["description"] = "Updated description"
        updated_payload["state"] = "off"

        resp = await client.put(f"{BASE_URL}/{flag_payload['key']}", json=updated_payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "Updated description"
        assert data["state"] == "off"

        # ---------------------------
        # DELETE FLAG
        # ---------------------------
        resp = await client.delete(f"{BASE_URL}/{flag_payload['key']}", headers=headers)
        assert resp.status_code == 204  # No content

        # Verify deletion
        resp = await client.get(f"{BASE_URL}/{flag_payload['key']}", headers=headers)
        assert resp.status_code == 404