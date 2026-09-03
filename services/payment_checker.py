from fastapi import HTTPException
from models import User, Transaction, TransactionStatus, Application
from schemas import TransactionForm, TransactionResponse
from datetime import datetime
from sqlalchemy import select
from database import Session
from services import service_role
from routers.card import charge

async def payment_checker_by_application_id(db: Session, user: service_role, application_id: int):
    current_time = datetime.utcnow().date()

    payments_db = await db.scalars(select(Transaction).where(
        Transaction.created_at < current_time,
        Transaction.application_id == application_id,
        Transaction.status != TransactionStatus.PROVIDED))
    payments = payments_db.all()

    application = await db.scalar(select(Application).where(Application.id==application_id))

    if not application:
        raise HTTPException(status_code=404, detail="SERVICE ERROR: Application does not exist")

    if not payments:
        form = TransactionForm(
            amount = application.amount + application.debt,
            application_id = 1
        )
        try:
            charge_response: TransactionResponse = charge(db,user,form)
        except:
            raise HTTPException(status_code=404, detail="SERVICE ERROR: Could not charge")