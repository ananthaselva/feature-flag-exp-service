# tests/test_integration_flags_crud.py
import pytest
import copy
from httpx import AsyncClient
from fastapi.encoders import jsonable_encoder
from app.main import app
from app.utils.security import issue_token

BASE_URL = "/v1/flags"
TENANT_ID = "acme"

@pytest.fixture
def auth_headers():
    token = issue_token("test_client", ["flags:rw"])
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID
    }

@pytest.mark.asyncio
async def test_flags_crud(auth_headers):
    flag_payload = {
        "key": "test_feature2",
        "description": "Feature toggle for testing",
        "state": "on",
        "variants": [
            {"key": "control", "weight": 50},
            {"key": "treatment", "weight": 50}
        ],
        "rules": [
            {
                "id": "r1",
                "order": 1,
                "when": {"percentage": 100},
                "rollout": {
                    "distribution": [
                        {"key": "control", "weight": 50},
                        {"key": "treatment", "weight": 50}
                    ]
                }
            }
        ]
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        # CREATE
        resp = await client.post(BASE_URL, json=jsonable_encoder(flag_payload), headers=auth_headers)
        assert resp.status_code in (200, 201)
        created = resp.json()
        assert created["key"] == flag_payload["key"]

        # READ
        resp = await client.get(f"{BASE_URL}/{flag_payload['key']}", headers=auth_headers)
        assert resp.status_code == 200
        read_data = resp.json()
        assert read_data["description"] == flag_payload["description"]

        # UPDATE
        updated = copy.deepcopy(flag_payload)
        updated["description"] = "Updated description"
        resp = await client.put(f"{BASE_URL}/{flag_payload['key']}", json=jsonable_encoder(updated), headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"

        # DELETE
        resp = await client.delete(f"{BASE_URL}/{flag_payload['key']}", headers=auth_headers)
        assert resp.status_code == 204

        # VERIFY deletion
        resp = await client.get(f"{BASE_URL}/{flag_payload['key']}", headers=auth_headers)
        assert resp.status_code == 404
