from fastapi import Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv
import os

load_dotenv()

# Supabase's session-mode pooler caps this project at 15 concurrent client
# connections total. SQLAlchemy's defaults (pool_size=5, max_overflow=10) let
# a single worker alone claim all 15 under load, so any second worker/replica
# guarantees EMAXCONNSESSION. Keep this worker's ceiling well under that.
engine = create_async_engine(
    os.getenv("DB_CONTEXT"),
    pool_size=3,
    max_overflow=2,
    pool_pre_ping=True,
    pool_recycle=1800,
)

new_session = async_sessionmaker(engine,expire_on_commit=False)

async def get_session():
    async with new_session() as session:
        yield session

Session = Annotated[AsyncSession,Depends(get_session)]