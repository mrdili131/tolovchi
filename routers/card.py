from fastapi import APIRouter, HTTPException
from models import Card, UserType
from database import Session
from services import user_dependency, service_role, user_role, InpayAutoPayService
from schemas import CardResponse, CardBindResponse
from sqlalchemy import select

router = APIRouter()


@router.get('/', response_model=list[CardResponse], status_code=200,summary="Gets user roled user cards")
async def get_cards(db: Session, user: user_role):
    cards = await db.scalars(select(Card).where(Card.user_id==user.get("id")))
    return cards.all()


@router.post('/bind',response_model=CardBindResponse,status_code=200)
async def card_bind(db: Session, user: user_role):
    inpay = InpayAutoPayService()
    resp = inpay.bind(customer_id=user.get("id"))
    bind_resp = CardBindResponse(
        card_link_url = resp["data"]["form_url"]
    )
    return bind_resp