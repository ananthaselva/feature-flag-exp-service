# conftest.py
import sys
import os
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.deps import get_db, engine
from app.models import Base
from app.utils.security import issue_token
from app.main import app

# -----------------------------
# Event loop for asyncio tests
# -----------------------------
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# -----------------------------
# Setup database (create tables)
# -----------------------------
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Optional teardown:
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)

# -----------------------------
# Provide AsyncSession to tests
# -----------------------------
@pytest_asyncio.fixture(scope="function")
async def db_session():
    session_gen = get_db()
    session = await anext(session_gen)
    try:
        yield session
    finally:
        await session.rollback()

# -----------------------------
# Auth token for API requests
# -----------------------------
@pytest.fixture(scope="function")
def auth_token():
    return issue_token(client_id="test-client", scopes=["read", "write"])

# -----------------------------
# Authorized HTTP client
# -----------------------------
@pytest_asyncio.fixture(scope="function")
async def authorized_client(auth_token):
    async with AsyncClient(app=app, base_url="http://test") as client:
        client.headers.update({
            "Authorization": f"Bearer {auth_token}",
            "X-Tenant-ID": "ABC"
        })
        yield client

# -----------------------------
# Public (unauthorized) HTTP client
# -----------------------------
@pytest_asyncio.fixture(scope="function")
async def public_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
