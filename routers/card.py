from fastapi import APIRouter, HTTPException
from datetime import date
from models import Card, User, UserType, Transaction, TransactionStatus, Application
from database import Session
from services import (
    user_role, service_auth, flexible_auth, InpayV2Service, ensure_inpay_customer, charge_saved_card,
    validate_charge_amount, apply_successful_charge, gross_up,
    PaginationParams, paginate,
)
from schemas import CardResponse, CardBindForm, CardBindResponse, CardVerifyForm, TransactionForm, TransactionResponse, SuccessResponse, PaginatedResponse
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

router = APIRouter()

# Each attempt (incl. "resend code") creates a card at InPay and sends an SMS;
# capping it per user per day stops SMS spam and card-number guessing.
MAX_CARD_BIND_ATTEMPTS_PER_DAY = 10


@router.get('/', response_model=PaginatedResponse[CardResponse], status_code=200, summary="Gets your bank cards. ROLES: [USER]")
async def get_cards(db: Session, user: user_role, params: PaginationParams):
    stmt = select(Card).where(Card.user_id==user.get("id"),Card.is_active==True).order_by(Card.id.desc())
    return await paginate(db, stmt, params)


@router.get('/detail/{card_id}', response_model=CardResponse, status_code=200,summary="Get a single card by id. ROLES: [USER]")
async def get_card(db: Session, user: user_role, card_id: int):
    card = await db.scalar(select(Card).where(Card.id==card_id).options(
        selectinload(Card.user)
    ))

    if not card:
        raise HTTPException(status_code=404, detail="This card does not exist")

    return card


def _expiry(exp_month, exp_year) -> str:
    return f"{int(exp_month):02d}/{int(exp_year) % 100:02d}" if exp_month and exp_year else ""


@router.post('/update', status_code=204, summary="Sync card statuses from the payment gateway. ROLES: [USER, SERVICE]")
async def update_cards(db: Session, user: flexible_auth):
    cards = (await db.scalars(select(Card).where(Card.user_id==user.get("id")))).all()
    if not cards:
        return

    inpay = InpayV2Service()
    for db_card in cards:
        remote = await inpay.get_card(db_card.charge_id)
        if remote and remote.get("status") == "active":
            info = remote.get("card") or {}
            db_card.pan = info.get("masked") or db_card.pan
            db_card.expiry = _expiry(info.get("exp_month"), info.get("exp_year")) or db_card.expiry
            db_card.is_active = True
        elif remote is None or remote.get("status") == "detached":
            db_card.is_active = False

    await db.commit()


@router.post('/bind',response_model=CardBindResponse,status_code=200,summary="Start binding a new card: InPay sends an SMS code to the card owner's phone. ROLES: [USER]")
async def card_bind(db: Session, user: user_role, form: CardBindForm):
    attempts_today = await db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id==user.get("id"), Card.created_at==date.today()
    ))
    if attempts_today >= MAX_CARD_BIND_ATTEMPTS_PER_DAY:
        raise HTTPException(status_code=429, detail="Bugun karta qo'shishga urinishlar soni tugadi. Ertaga qayta urinib ko'ring.")

    inpay = InpayV2Service()
    db_user = await db.get(User, user.get("id"))
    customer_id = await ensure_inpay_customer(db, inpay, db_user)
    resp = await inpay.create_card(card_number=form.card_number, expire_date=form.expire_date, customer_id=customer_id)
    info = resp.get("card") or {}

    card = Card(
        bind_ref = resp["id"],
        charge_id = resp["id"],
        holder = {"uzcard": "Uzcard", "humo": "Humo"}.get(info.get("brand"), "Karta"),
        pan = info.get("masked") or resp.get("card_masked") or "",
        expiry = _expiry(info.get("exp_month"), info.get("exp_year")),
        is_active = False,
        user_id = user.get("id")
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)

    return CardBindResponse(card_id=card.id, phone_masked=resp.get("phone_masked"), wait_ms=resp.get("wait_ms"))


@router.post('/bind/verify',response_model=CardResponse,status_code=200,summary="Confirm card binding with the SMS code. ROLES: [USER]")
async def card_bind_verify(db: Session, user: user_role, form: CardVerifyForm):
    card = await db.scalar(select(Card).where(Card.id==form.card_id,Card.user_id==user.get("id")))
    if not card:
        raise HTTPException(status_code=404, detail="Karta topilmadi. Kartani qaytadan qo'shing.")

    if card.is_active:
        raise HTTPException(status_code=400, detail="Bu karta allaqachon tasdiqlangan.")

    resp = await InpayV2Service().verify_card(card.charge_id, form.code.strip())

    if resp.get("status") != "active":
        raise HTTPException(status_code=400, detail="SERVICE ERROR: Kartani tasdiqlab bo'lmadi. Kodni tekshirib, qayta urinib ko'ring.")

    info = resp.get("card") or {}
    card.pan = info.get("number") or card.pan
    card.expiry = info.get("expire") or card.expiry
    card.is_active = True
    await db.commit()
    await db.refresh(card)

    return card


@router.post('/remove/{card_id}', response_model=SuccessResponse , status_code=200, summary="Remove card from platform. ROLES: [USER]")
async def remove_card(db: Session, user: user_role, card_id: int):
    card = await db.scalar(select(Card).where(Card.id==card_id,Card.user_id==user.get("id")))
    if not card:
        raise HTTPException(status_code=404, detail="Karta topilmadi.")

    if not card.is_active:
        raise HTTPException(status_code=400, detail="Bu karta allaqachon o'chirilgan.")

    res = await InpayV2Service().remove_card(card.charge_id)

    if not res:
        raise HTTPException(status_code=400, detail="SERVICE ERROR: Kartani to'lov tizimidan uzib bo'lmadi. Qayta urinib ko'ring.")

    card.is_active = False
    await db.commit()

    return SuccessResponse(status=True, detail="Success")



@router.post('/charge',response_model=TransactionResponse,status_code=200,summary="Charge a client's card for an application. ROLES: [SERVICE]")
async def charge(db: Session, user: service_auth, form: TransactionForm):
    service = await db.get(User,user.get("id"))
    application = await db.get(Application,form.application_id)

    if not service or service.role != UserType.SERVICE or not application:
        raise HTTPException(status_code=404,detail="Service or application is not valid")

    if application.service_id != user.get("id"):
        raise HTTPException(status_code=403,detail="Cannot charge for this application")

    validate_charge_amount(application, form.amount)

    cards_res = await db.scalars(select(Card).where(Card.user_id==application.payer_id, Card.is_active==True))
    cards = cards_res.all()

    if not cards:
        raise HTTPException(status_code=404, detail="Payer has no active cards")

    payer = await db.get(User, application.payer_id)
    inpay = InpayV2Service()
    last_error = "Could not provide transaction"
    gross_amount = gross_up(form.amount)

    for card in cards:
        transaction = Transaction(
            amount = form.amount,
            fee_amount = gross_amount - form.amount,
            sender_id = card.user_id,
            receiver_id = service.id,
            application_id = application.id,
        )

        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        try:
            await charge_saved_card(inpay, payer, card, gross_amount, transaction, description=application.name)

            apply_successful_charge(application, form.amount)
            service.balance += form.amount

            transaction.status = TransactionStatus.PROVIDED

            db.add(transaction)
            await db.commit()
            await db.refresh(service)
            await db.refresh(transaction)
            await db.refresh(application)

            return await db.scalar(select(Transaction).where(Transaction.id==transaction.id).options(
                selectinload(Transaction.sender),
                selectinload(Transaction.receiver),
                selectinload(Transaction.application)
            ))
        except HTTPException as exc:
            transaction.status = TransactionStatus.REJECTED
            await db.commit()
            last_error = exc.detail
            continue

    raise HTTPException(status_code=400, detail=last_error)
