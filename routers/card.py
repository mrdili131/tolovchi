from fastapi import APIRouter, HTTPException
from models import Card, User, UserType, Transaction, TransactionStatus
from database import Session
from services import user_dependency, service_role, user_role, InpayAutoPayService
from schemas import CardResponse, CardBindResponse, TransactionForm, TransactionResponse
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

router = APIRouter()


@router.get('/', response_model=list[CardResponse], status_code=200,summary="Gets cards, ROLES: [USER]")
async def get_cards(db: Session, user: user_role):
    cards = await db.scalars(select(Card).where(Card.user_id==user.get("id"),Card.is_active==True))
    return cards.all()


@router.get('/update', status_code=204,summary="Updates cards, ROLES: [USER, SERVICE]")
async def update_cards(db: Session, user: user_dependency):
    inpay = InpayAutoPayService()
    response = inpay.list_cards(user.get("id"))

    for card in response["data"]["cards"]:
        db_card = await db.scalar(select(Card).where(Card.charge_id==card["id"]))
        if db_card and card["status"] == "active":
            db_card.holder = card["holder"]
            db_card.user_id = card["customer_ref"]
            db_card.pan = card["masked_pan"]
            db_card.expiry = card["expiry"]
            db_card.is_active = True
            await db.commit()
            await db.refresh(db_card)
        elif db_card and card["status"] != "active":
            db_card.is_active = False
            await db.commit()
            await db.refresh(db_card)


@router.get('/bind',response_model=CardBindResponse,status_code=200,summary="Binding cards, ROLES: [USER]")
async def card_bind(db: Session, user: user_role, return_url: str):
    inpay = InpayAutoPayService()
    resp = inpay.bind(customer_id=user.get("id"),return_url=return_url)
    bind_resp = CardBindResponse(
        card_link_url = resp["data"]["form_url"]
    )
    card = Card(
        bind_ref = resp["data"]["bind_ref"],
        charge_id = resp["data"]["card_id"],
        user_id = user.get("id")
    )
    db.add(card)
    await db.commit()

    return bind_resp


@router.post('/charge',response_model=TransactionResponse,status_code=200,summary="Charing amount, ROLES: [SERVICE]")
async def charge(db: Session, user: service_role, form: TransactionForm):
    service = await db.get(User,form.service_id)
    card = await db.get(Card,form.card_id)

    if not card or not service or service.type != UserType.SERVICE:
        raise HTTPException(status_code=404,detail="Service or card is not valid")

    inpay = InpayAutoPayService()
    transaction = Transaction(
        amount = form.amount,
        sender_id = card.user_id,
        receiver_id = form.service_id
    )
    db.add(transaction)
    await db.commit()

    res = inpay.charge(amount=form.amount,card_id=card.charge_id)

    if not res:
        raise HTTPException(status_code=400,detail="Could not charge")

    service.balance += form.amount

    transaction.status = TransactionStatus.PROVIDED

    await db.commit()
    await db.refresh(transaction)
    await db.refresh(service)

    result = await db.scalar(select(Transaction).where(Transaction.id==transaction.id).options(
        selectinload(Transaction.sender),
        selectinload(Transaction.receiver)
    ))

    return transaction


@router.get('/transactions',response_model=list[TransactionResponse],status_code=200,summary="Get transactions, ROLES: [USER, SERVICE]")
async def get_transactions(db: Session, user: user_dependency):
    transactions = await db.scalars(select(Transaction).filter(
        or_(
            Transaction.sender_id==user.get("id"),
            Transaction.receiver_id==user.get("id")))
        .options(
            selectinload(Transaction.sender),
            selectinload(Transaction.receiver)
        ))
    return transactions.all()