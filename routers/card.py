from fastapi import APIRouter, HTTPException
from models import Card, User, UserType, Transaction, TransactionStatus, Application
from database import Session
from services import (
    user_role, service_auth, flexible_auth, InpayAutoPayService,
    validate_charge_amount, apply_successful_charge, gross_up,
    PaginationParams, paginate,
)
from schemas import CardResponse, CardBindResponse, TransactionForm, TransactionResponse, SuccessResponse, PaginatedResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

router = APIRouter()


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


@router.post('/update', status_code=204, summary="Sync card statuses from the payment gateway. ROLES: [USER, SERVICE]")
async def update_cards(db: Session, user: flexible_auth):
    inpay = InpayAutoPayService()
    response = inpay.list_cards(user.get("id"))

    for card in response["data"]["cards"]:
        db_card = await db.scalar(select(Card).where(Card.charge_id==card["id"]))
        if db_card and card["status"] == "active":
            db_card.holder = card["holder"]
            db_card.user_id = int(card["customer_ref"])
            db_card.pan = card["masked_pan"]
            db_card.expiry = card["expiry"]
            db_card.is_active = True
            await db.commit()
            await db.refresh(db_card)
        elif db_card and card["status"] != "active":
            db_card.is_active = False
            await db.commit()
            await db.refresh(db_card)


@router.post('/bind',response_model=CardBindResponse,status_code=200,summary="Start binding a new card. ROLES: [USER]")
async def card_bind(db: Session, user: user_role, return_url: str):
    inpay = InpayAutoPayService()
    resp = inpay.bind(customer_id=user.get("id"),return_url=return_url)
    bind_resp = CardBindResponse(
        card_link_url = resp["data"]["form_url"]
    )
    card = Card(
        bind_ref = resp["data"]["bind_ref"],
        charge_id = int(resp["data"]["card_id"]),
        user_id = user.get("id")
    )
    db.add(card)
    await db.commit()

    return bind_resp


@router.post('/remove/{card_id}', response_model=SuccessResponse , status_code=200, summary="Remove card from platform. ROLES: [USER]")
async def remove_card(db: Session, user: user_role, card_id: int):
    card = await db.scalar(select(Card).where(Card.id==card_id,Card.user_id==user.get("id")))
    if not card:
        raise HTTPException(status_code=404, detail="Card is not found")

    if not card.is_active:
        raise HTTPException(status_code=400, detail="Card is already deactivated")

    inpay = InpayAutoPayService()
    res = inpay.remove(card.charge_id)

    if not res:
        raise HTTPException(status_code=400, detail="Could not remove card")

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

    inpay = InpayAutoPayService()
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
            inpay.charge(amount=gross_amount, card_id=card.charge_id, idem_key=f"txn-{transaction.id}")

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
