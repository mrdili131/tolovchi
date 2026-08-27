from fastapi import APIRouter, HTTPException
from models import Card, User, UserType, Transaction, TransactionStatus
from database import Session
from services import user_dependency, service_role, user_role, InpayAutoPayService
from schemas import CardResponse, CardBindResponse, TransactionForm, TransactionResponse
from sqlalchemy import select

router = APIRouter()


@router.get('/', response_model=list[CardResponse], status_code=200,summary="Gets user roled user cards")
async def get_cards(db: Session, user: user_role):
    cards = await db.scalars(select(Card).where(Card.user_id==user.get("id")))
    return cards.all()


@router.get('/bind',response_model=CardBindResponse,status_code=200,summary="Binding cards for user role")
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


@router.post('/charge',response_model=TransactionResponse,status_code=200,summary="Charing amount for service roles")
async def charge(db: Session, user: service_role, form: TransactionForm):
    service = await db.get(User,form.service_id)
    card = await db.get(Card,form.card_id)

    if not card or not service:
        raise HTTPException(status_code=404,detail="Service or card is not valid")

    inpay = InpayAutoPayService()
    transaction = Transaction(
        amount = form.amount,
        sender_id = user.get("id"),
        receiver_id = form.service_id
    )
    db.add(transaction)
    await db.commit()

    res = inpay.charge(amount=form.amount,card_id=form.card_id)

    if not res:
        raise HTTPException(status_code=400,detail="Could not charge")

    service.balance += form.amount

    transaction.status = TransactionStatus.PROVIDED

    await db.commit()
    await db.refresh(transaction)
    await db.refresh(service)

    return transaction


@router.get('/transactions',response_class=TransactionResponse,status_code=200,summary="Gets transactions based on role")
async def get_transactions(db: Session, user: user_dependency):
    if user.get("role") == UserType.USER.value:
        transactions = await db.scalars(select(Transaction).where(Transaction.sender_id==user.get("id")))
        return transactions.all()
    elif user.get("role") == UserType.SERVICE.value:
        transactions = await db.scalars(select(Transaction).where(Transaction.receiver_id==user.get("id")))
        return transactions.all()
    else:
        raise HTTPException(status_code=400,detail="Could not get transactions")