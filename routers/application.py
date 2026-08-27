from fastapi import APIRouter, HTTPException
from models import User, UserType, Application
from database import Session
from services import user_dependency
from schemas import ApplicationResponse
from sqlalchemy import select

router = APIRouter()

@router.get('/', response_model=list[ApplicationResponse], status_code=200, summary="Get applications based on your role. Service's app or client connected app")
async def get_applications(user: user_dependency, db: Session):
    match user.get("role"):
        case UserType.USER.value:
            applications = await db.scalars(select(Application).where(Application.payer_id==user.get("id")))
            return applications.all()
        case UserType.SERVICE.value:
            applications = await db.scalars(select(Application).where(Application.service_id==user.get("id")))
            return applications.all()
        case _:
            raise HTTPException(status_code=404, detail="Not found")