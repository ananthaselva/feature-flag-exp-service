# conftest.py
import sys
import os
import asyncio
import pytest

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.deps import get_db, engine
from app.models import Base

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
@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Optional: drop tables after tests
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)


# -----------------------------
# Provide AsyncSession to tests
# -----------------------------
@pytest.fixture
async def db_session():
    """
    Properly yield an AsyncSession instance for tests.
    """
    async for session in get_db():
        try:
            yield session
        finally:
            await session.rollback()
