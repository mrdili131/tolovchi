from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import new_session
from services import payment_checker
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


async def schedule_wrapper():
    async with new_session() as db:
        try:
            await payment_checker(db=db)
        except Exception as e:
            print(e)

@asynccontextmanager
async def lifespan_scheduler(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        schedule_wrapper,
        trigger=CronTrigger(hour=8,minute=0,second=0),
        id="daily_payment_checking",
        replace_existing=True
    )
    scheduler.start()
    print("SYSTEM Avto to‘lov ishga tushdi",flush=True)
    yield
    scheduler.shutdown()
    print("SYSTEM Avto to‘lov yakunladi")