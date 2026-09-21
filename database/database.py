from fastapi import Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv
import os

load_dotenv()

# Supabase's session-mode pooler caps this project at 15 concurrent client
# connections total. This app autoscales up to 3 replicas, each with its own
# independent pool — so the per-replica ceiling here must leave real headroom
# below 15/3, not just divide evenly, to survive rolling-deploy overlap
# (old + new replica briefly alive together), migrations, and Supabase
# Studio. 3 per replica x 3 replicas = 9, leaving 6 connections of slack.
engine = create_async_engine(
    os.getenv("DB_CONTEXT"),
    pool_size=2,
    max_overflow=1,
    pool_pre_ping=True,
    pool_recycle=1800,
)

new_session = async_sessionmaker(engine,expire_on_commit=False)

async def get_session():
    async with new_session() as session:
        yield session

Session = Annotated[AsyncSession,Depends(get_session)]