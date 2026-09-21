import math
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from sqlalchemy import select, extract
from models import Application, PaymentAttempt, PayoutRequest, PayoutStatus

# InPay charges this cut on every gateway charge. We gross the customer's
# charge up by this rate so the service still nets the full agreed amount.
INPAY_FEE_RATE = 0.06

MIN_PAYOUT_AMOUNT = 100_000

# Reason text used when a linked application has no active card to charge yet.
# Still counts toward the normal 3-strike cutoff, same as any other decline —
# a customer has 3 daily attempts to get a working card on file before the
# application is closed.
NO_ACTIVE_CARDS_REASON = "No active cards on file"


def gross_up(net_amount: int) -> int:
    """Amount to actually charge the customer's card: the service's agreed
    price plus a flat 6% surcharge — exactly 6%, not 6% of the charged total."""
    return math.ceil(net_amount * (1 + INPAY_FEE_RATE))


def validate_charge_amount(application: Application, amount: int):
    if application.is_paid:
        raise HTTPException(status_code=400, detail="Application is already paid for this cycle")
    if amount > application.amount:
        raise HTTPException(status_code=400, detail="Cannot charge more than the agreed application amount")


async def validate_payout_request(db, service, amount: int):
    if amount < MIN_PAYOUT_AMOUNT:
        raise HTTPException(status_code=400, detail=f"Minimum payout amount is {MIN_PAYOUT_AMOUNT} so'm")
    if amount > service.balance:
        raise HTTPException(status_code=400, detail=f"Cannot withdraw more than your current balance ({service.balance} so'm)")

    pending = await db.scalar(select(PayoutRequest).where(
        PayoutRequest.service_id == service.id,
        PayoutRequest.status == PayoutStatus.PENDING,
    ))
    if pending:
        raise HTTPException(status_code=400, detail="You already have a pending payout request")

    current_date = datetime.utcnow().date()
    paid_this_month = await db.scalar(select(PayoutRequest).where(
        PayoutRequest.service_id == service.id,
        PayoutRequest.status == PayoutStatus.PAID,
        extract('year', PayoutRequest.processed_at) == current_date.year,
        extract('month', PayoutRequest.processed_at) == current_date.month,
    ))
    if paid_this_month:
        raise HTTPException(status_code=400, detail="You can only request one payout per calendar month")


def apply_successful_charge(application: Application, amount: int):
    current_date = datetime.utcnow().date()

    # First successful charge is what actually activates the subscription —
    # a QR scan alone no longer does (see apply_failed_attempt / link()).
    application.is_active = True
    application.is_paid = True
    application.failed_attempts = 0
    application.balance += amount
    application.debt = max(application.debt - amount, 0)
    application.next_payment = current_date + relativedelta(months=1, day=application.pay_day)


async def apply_failed_attempt(db, application: Application, reason: str):
    application.is_paid = False
    application.failed_attempts += 1

    attempt = PaymentAttempt(
        application_id=application.id,
        success=False,
        reason=reason,
        attempt_number=application.failed_attempts,
    )
    db.add(attempt)

    if application.failed_attempts >= 3:
        current_date = datetime.utcnow().date()
        application.is_active = False
        application.end_date = current_date

    await db.commit()
    await db.refresh(application)


async def log_successful_attempt(db, application: Application):
    attempt = PaymentAttempt(
        application_id=application.id,
        success=True,
        reason=None,
        attempt_number=application.failed_attempts,
    )
    db.add(attempt)
    await db.commit()
