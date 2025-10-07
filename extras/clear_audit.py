# clear_audit.py
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models import Audit  # your SQLAlchemy model




# Replace with your actual DB URL
DATABASE_URL = "sqlite+aiosqlite:///./dev.db"

async def clear_audit_table():
    # Create async engine and session
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        # Delete all records from Audit table
        await session.execute(Audit.__table__.delete())
        await session.commit()
        print("All audit records deleted successfully.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(clear_audit_table())
