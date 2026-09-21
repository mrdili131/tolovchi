from models import TransactionStatus, Application, User, Card, Transaction
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select, or_, and_
from database import Session
from services import InpayAutoPayService
from services.billing_service import (
    apply_successful_charge, apply_failed_attempt, log_successful_attempt, gross_up,
    NO_ACTIVE_CARDS_REASON,
)
from services.webhook_service import send_webhook


async def _fail_and_maybe_notify(db: Session, app: Application, service_user: User | None, reason: str):
    """Runs the standard 3-strike failure bookkeeping, then fires the service's
    webhook if this attempt was the one that closed the application."""
    await apply_failed_attempt(db, app, reason=reason)
    if app.end_date and service_user:
        await send_webhook(service_user.webhook_url, "application.deactivated", {
            "application_id": app.id,
            "reason": reason,
        })


async def process_application(db: Session, app: Application):
    """Attempts to collect a single due application's payment, and records the
    outcome. Shared by the daily scheduled job and the admin manual-retry endpoint."""

    current_date = datetime.utcnow().date()

    app.is_paid = False

    service_user = await db.get(User, app.service_id)
    client_user = await db.get(User, app.payer_id)

    if not service_user or not client_user:
        await _fail_and_maybe_notify(db, app, service_user, reason="Service or payer account is missing")
        app.last_checked_at = current_date
        await db.commit()
        return

    cards = await db.scalars(select(Card).where(Card.user_id==app.payer_id, Card.is_active==True))
    cards = cards.all()

    if not cards:
        await _fail_and_maybe_notify(db, app, service_user, reason=NO_ACTIVE_CARDS_REASON)
        app.last_checked_at = current_date
        await db.commit()
        return

    inpay = InpayAutoPayService()
    last_error = "Could not charge any of the payer's cards"
    gross_amount = gross_up(app.amount)

    for card in cards:
        transaction = Transaction(
            amount = app.amount,
            fee_amount = gross_amount - app.amount,
            status = TransactionStatus.PENDING,
            sender_id = client_user.id,
            receiver_id = service_user.id,
            application_id = app.id
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        try:
            inpay.charge(card_id=card.charge_id, amount=gross_amount, idem_key=f"txn-{transaction.id}", reason="BINDIN AVTO-TO‘LOV TIZIMI")

            apply_successful_charge(app, app.amount)
            service_user.balance += app.amount

            transaction.status = TransactionStatus.PROVIDED
            app.last_checked_at = current_date

            await db.commit()
            await log_successful_attempt(db, app)
            return
        except HTTPException as exc:
            transaction.status = TransactionStatus.REJECTED
            await db.commit()
            last_error = str(exc.detail)
            continue

    await _fail_and_maybe_notify(db, app, service_user, reason=last_error)
    app.last_checked_at = current_date
    await db.commit()


async def payment_checker(db: Session):

    current_date = datetime.utcnow().date()

    applications_db = await db.scalars(select(Application).where(
        or_(
            # Normal recurring case: active subscription whose next cycle is due.
            and_(Application.is_active == True, Application.next_payment <= current_date),
            # First-charge case: linked (has a payer) but never successfully
            # charged yet, and not permanently closed (end_date unset).
            and_(Application.is_active == False, Application.payer_id != None, Application.end_date == None),
        ),
        or_(Application.last_checked_at == None, Application.last_checked_at < current_date)
    ))

    for app in applications_db.all():
        try:
            await process_application(db, app)
        except Exception as e:
            print(f"[AUTO-PAYMENT] Failed to process application {app.id}: {e}")

    print("[AUTO-PAYMENT] PAYMENT CYCLE HAS BEEN DONE")
