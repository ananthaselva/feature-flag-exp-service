import sys
import os

# Add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import SessionLocal
from app.models import Flag
from app.schemas import FlagIn

TENANT_ID = "ABC"

async def seed_flags():
    async with SessionLocal() as db:
        for i in range(1, 21):
            key = f"feature_{i}"
            
            # Check if flag already exists (skip if exists)
            exists = (
                await db.execute(
                    select(Flag).where(Flag.tenant_id == TENANT_ID, Flag.key == key)
                )
            ).scalar_one_or_none()
            if exists:
                continue
            
            # 10 flags on, 10 flags off
            state = "on" if i <= 10 else "off"
            
            new_flag = Flag(
                tenant_id=TENANT_ID,
                key=key,
                description=f"Feature {i} for tenant {TENANT_ID}",
                state=state,
                variants=[{"key": "control", "weight": 50}, {"key": "treatment", "weight": 50}],
                rules=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(new_flag)
        await db.commit()
        print(f"Seeded 20 unique flags for tenant {TENANT_ID}.")


if __name__ == "__main__":
    asyncio.run(seed_flags())