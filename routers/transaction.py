from fastapi import APIRouter, HTTPException
from models import Transaction
from database import Session
from services import user_dependency
from schemas import TransactionResponse
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload


router = APIRouter()


@router.get('/',response_model=list[TransactionResponse],status_code=200,summary="Get transactions, ROLES: [USER, SERVICE]")
async def get_transactions(db: Session, user: user_dependency):
    transactions = await db.scalars(select(Transaction).filter(
        or_(
            Transaction.sender_id==user.get("id"),
            Transaction.receiver_id==user.get("id")))
        .options(
            selectinload(Transaction.sender),
            selectinload(Transaction.receiver),
            selectinload(Transaction.application)
        ).order_by(Transaction.id.desc()))
    return transactions.all()


@router.get('/detail/{transaction_id}', response_model=TransactionResponse, status_code=200, summary="Get transaction by id. ROLES: [USER, SERVICE]")
async def get_transaction(db: Session, user: user_dependency, transaction_id: int):
    transaction = await db.scalar(select(Transaction).where(Transaction.id==transaction_id).options(
        selectinload(Transaction.sender),
        selectinload(Transaction.receiver),
        selectinload(Transaction.application)
    ))

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction does not exist")

    return transaction