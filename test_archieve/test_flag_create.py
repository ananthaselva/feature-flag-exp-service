import asyncio
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.flags import create_flag
from app.schemas import FlagIn
from app.deps import get_db

# Example payload
payload = FlagIn(
    key="string",
    description="string",
    state="on",
    variants=[{"key": "string", "weight": 100}],
    rules=[]
)

TENANT_ID = "my_test_tenant"

async def run_create_flag():
    async for db in get_db():  # get AsyncSession
        response = await create_flag(flag_in=payload, tenant=TENANT_ID, db=db)
        # If JSONResponse, decode body
        if hasattr(response, "body"):
            print("Create Flag Response:", response.body.decode())
        else:
            print("Create Flag Response:", jsonable_encoder(response))

if __name__ == "__main__":
    asyncio.run(run_create_flag())