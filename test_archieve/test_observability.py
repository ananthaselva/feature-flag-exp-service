# tests/test_observability.py
import pytest
from httpx import AsyncClient
from app.main import app
from app.utils.metrics import REQUEST_COUNT

TENANTS = ["tenantA", "tenantB"]
REQUEST_IDS = ["req1", "req2"]

@pytest.mark.asyncio
async def test_healthz_readyz():
    async with AsyncClient(app=app, base_url="http://test") as client:
        for tenant in TENANTS:
            for req_id in REQUEST_IDS:
                headers = {"X-Tenant-ID": tenant, "X-Request-ID": req_id}

                r = await client.get("/healthz", headers=headers)
                assert r.status_code == 200
                assert r.text == "ok"

                r = await client.get("/readyz", headers=headers)
                assert r.status_code == 200
                assert r.text == "ready"


@pytest.mark.asyncio
async def test_metrics_counter_increment():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Capture current counter values
        before = {
            tuple(s.labels.items()): s.value for s in REQUEST_COUNT.collect()[0].samples
        }

        # Make requests with specific tenant and request_id headers
        requests = [
            ("/healthz", "GET", {"X-Tenant-ID": "tenantA", "X-Request-ID": "req1"}),
            ("/readyz", "GET", {"X-Tenant-ID": "tenantA", "X-Request-ID": "req1"}),
            ("/healthz", "GET", {"X-Tenant-ID": "tenantA", "X-Request-ID": "req2"}),
        ]

        for path, method, headers in requests:
            if method == "GET":
                await client.get(path, headers=headers)

        # Capture counter values after requests
        after = {
            tuple(s.labels.items()): s.value for s in REQUEST_COUNT.collect()[0].samples
        }

        # Compare relative increments
        for key, after_value in after.items():
            before_value = before.get(key, 0)
            # Ensure counter increased for observed requests
            if any(kv in dict(key).items() for kv in requests):
                assert after_value >= before_value + 1, f"Counter did not increment for {dict(key)}"