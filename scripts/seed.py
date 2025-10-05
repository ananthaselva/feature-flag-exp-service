import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import SessionLocal
from app.models import Flag, Segment


async def seed():
    async with SessionLocal() as db:
        # tenant 'acme'
        exists = (
            await db.execute(
                select(Flag).where(Flag.tenant_id == "acme", Flag.key == "new_checkout")
            )
        ).scalar_one_or_none()
        if not exists:
            f = Flag(
                tenant_id="acme",
                key="new_checkout",
                description="New checkout flow",
                state="on",
                variants=[
                    {"key": "control", "weight": 50},
                    {"key": "treatment", "weight": 50},
                ],
                rules=[
                    {
                        "id": "r1",
                        "order": 1,
                        "when": {"attr": {"role": "employee"}},
                        "rollout": {"variant": "treatment"},
                    },
                    {
                        "id": "r2",
                        "order": 2,
                        "when": {"percentage": 50},
                        "rollout": {
                            "distribution": [
                                {"key": "control", "weight": 50},
                                {"key": "treatment", "weight": 50},
                            ]
                        },
                    },
                ],
            )
            db.add(f)
        seg = (
            await db.execute(
                select(Segment).where(
                    Segment.tenant_id == "acme", Segment.key == "internal"
                )
            )
        ).scalar_one_or_none()
        if not seg:
            s = Segment(
                tenant_id="acme",
                key="internal",
                criteria={"attr": {"role": "employee"}},
            )
            db.add(s)
        await db.commit()
        print("Seeded sample flags and segments for tenant 'acme'.")


if __name__ == "__main__":
    asyncio.run(seed())
