import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_and_ready():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/healthz")
        assert r.status_code == 200 and r.text == "ok"
        r = await ac.get("/readyz")
        assert r.status_code == 200 and r.text == "ready"
