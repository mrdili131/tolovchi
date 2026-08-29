from fastapi import APIRouter, HTTPException
from models import User, UserType, Application
from database import Session
from services import user_dependency, service_role, user_role
from schemas import ApplicationResponse, ApplicationForm, SuccessResponse
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


@router.post('/',status_code=200,summary="Create an application. ROLES: [SERVICE]")
async def create_application(db: Session, user: service_role, form: ApplicationForm):
    new_application = Application(
        name = form.name,
        description = form.description,
        amount = form.amount,
        service_id = user.get("id")
    )
    db.add(new_application)
    await db.commit()



@router.post('/link/{application_id}', response_model=SuccessResponse,status_code=200,summary="For linking user to application. QR code usage. ROLES: [USER]")
async def link(db: Session, user: user_role, application_id: int):

    application = await db.get(Application,application_id)
    if not application or application.is_active or application.payer_id:
        raise HTTPException(status_code=400, detail="Application does not exist or is already activated")

    application.payer_id = user.get("id")
    application.is_active = True

    await db.commit()
    await db.refresh(application)

    return SuccessResponse(status=True,detail=f"User linked to {application.name}")
