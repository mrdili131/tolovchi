from models import TransactionStatus, Application, User, Card, Transaction
from schemas import TransactionStatus
from datetime import datetime
from sqlalchemy import select
from database import Session
from services import InpayAutoPayService
from dateutil.relativedelta import relativedelta


async def payment_checker(db: Session):

    current_date = datetime.utcnow().date()
    inpay = InpayAutoPayService()

    applications_db = await db.scalars(select(Application).where(
        Application.is_active == True,
        Application.is_paid == False,
        Application.next_payment <= current_date
    ))

    for app in applications_db.all():

        service_user = await db.get(User,app.service_id)
        client_user = await db.get(User,app.payer_id)
        cards = await db.scalars(select(Card).where(Card.user_id==app.payer_id))


        for card in cards.all():
            resp = inpay.charge(card.id,app.amount,reason="BINDIN AVTO-TO‘LOV TIZIMI")
            if resp.get("success") == True:

                new_transaction = Transaction(
                    amount = app.amount,
                    status = TransactionStatus.PROVIDED,
                    sender_id = client_user.id,
                    receiver_id = service_user.id,
                    application_id = app.id
                )

                app.is_paid = True
                app.next_payment = current_date + relativedelta(months=1, day=app.pay_day)

                db.add(new_transaction)
                await db.commit()
                await db.refresh(app)
                break


    print("[AUTO-PAYMENT] PAYMENT CYCLE HAS BEEN DONE")