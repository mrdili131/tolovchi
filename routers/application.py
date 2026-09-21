from fastapi import APIRouter, HTTPException
from models import UserType, Application
from database import Session
from services import service_auth, flexible_auth, user_role, PaginationParams, paginate
from services.payment_checker import process_application
from schemas import ApplicationResponse, ApplicationForm, SuccessResponse, PaginatedResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

router = APIRouter()

@router.get('/', response_model=PaginatedResponse[ApplicationResponse], status_code=200, summary="Get applications based on your role. Service's app or client connected app. ROLES: [USER, SERVICE]")
async def get_applications(user: flexible_auth, db: Session, params: PaginationParams):
    match user.get("role"):
        case UserType.USER.value:
            stmt = select(Application).where(Application.payer_id==user.get("id")).options(
                selectinload(Application.payer),
                selectinload(Application.service)
            ).order_by(Application.id.desc())
        case UserType.SERVICE.value:
            stmt = select(Application).where(Application.service_id==user.get("id")).options(
                selectinload(Application.payer),
                selectinload(Application.service)
            ).order_by(Application.id.desc())
        case _:
            raise HTTPException(status_code=404, detail="Not found")

    return await paginate(db, stmt, params)


@router.post('/', response_model=ApplicationResponse, status_code=201, summary="Create an application. ROLES: [SERVICE]")
async def create_application(db: Session, user: service_auth, form: ApplicationForm):
    new_application = Application(
        name = form.name,
        description = form.description,
        amount = form.amount,
        frequency = form.frequency,
        pay_day = form.pay_day,
        service_id = user.get("id")
    )
    db.add(new_application)
    await db.commit()
    await db.refresh(new_application)

    return await db.scalar(select(Application).where(Application.id==new_application.id).options(
        selectinload(Application.payer),
        selectinload(Application.service)
    ))


@router.get('/detail/{app_id}', response_model=ApplicationResponse, status_code=200, summary="Get application by app id. ROLES: [USER, SERVICE]")
async def get_application(db: Session, user: flexible_auth, app_id: int):
    application = await db.scalar(select(Application).where(Application.id==app_id).options(
        selectinload(Application.payer),
        selectinload(Application.service)
    ))

    if not application:
        raise HTTPException(status_code=404, detail="Application does not exist")

    return application


@router.post('/link/{application_id}', response_model=SuccessResponse,status_code=200,summary="Link to an application and attempt the first charge immediately. QR code usage. ROLES: [USER]")
async def link(db: Session, user: user_role, application_id: int):

    application = await db.get(Application,application_id)
    if not application or application.payer_id:
        raise HTTPException(status_code=400, detail="Application does not exist or is already claimed")

    application.payer_id = user.get("id")
    await db.commit()
    await db.refresh(application)

    # is_active only flips to True once this first charge actually succeeds —
    # a scan alone is not proof of payment. See apply_successful_charge /
    # apply_failed_attempt in services/billing_service.py.
    await process_application(db, application)
    await db.refresh(application)

    if application.is_active:
        return SuccessResponse(status=True, detail=f"Linked to {application.name} and first payment succeeded")
    if application.end_date:
        return SuccessResponse(status=False, detail=f"Linked to {application.name}, but payment failed and the application was closed")
    return SuccessResponse(status=True, detail=f"Linked to {application.name}. First payment could not be completed yet — the system will keep retrying")


@router.post('/unlink/{application_id}', response_model=SuccessResponse, status_code=200, summary="Cancel an application you're subscribed to. ROLES: [USER]")
async def unlink_application(db: Session, user: user_role, application_id: int):
    app = await db.scalar(select(Application).where(
        Application.id == application_id,
        Application.payer_id == user.get("id"),
        Application.end_date == None
    ))

    if not app:
        raise HTTPException(status_code=404, detail="Could not find application")

    app.is_active = False
    app.end_date = datetime.utcnow().date()

    await db.commit()
    await db.refresh(app)

    return SuccessResponse(status=True, detail="Success")


@router.post('/{application_id}/charge', response_model=SuccessResponse, status_code=200, summary="Manually attempt to charge one of your own applications right now, e.g. within its 3-day retry window. ROLES: [SERVICE]")
async def charge_application_now(db: Session, user: service_auth, application_id: int):
    application = await db.scalar(select(Application).where(
        Application.id == application_id,
        Application.service_id == user.get("id"),
    ))
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.end_date:
        raise HTTPException(status_code=400, detail="Application is closed")
    if not application.payer_id:
        raise HTTPException(status_code=400, detail="Application has no payer linked yet")
    if application.is_paid:
        raise HTTPException(status_code=400, detail="Application is already paid for this cycle")

    await process_application(db, application)
    await db.refresh(application)

    if application.is_active:
        return SuccessResponse(status=True, detail="Payment succeeded")
    if application.end_date:
        return SuccessResponse(status=False, detail="Payment failed and the application was closed")
    return SuccessResponse(status=False, detail="Payment could not be completed")


@router.post('/stop/{application_id}', response_model=SuccessResponse, status_code=200, summary="Stop an application you own. ROLES: [SERVICE]")
async def stop_application(db: Session, user: service_auth, application_id: int):
    app = await db.scalar(select(Application).where(
        Application.id == application_id,
        Application.service_id == user.get("id"),
        Application.end_date == None
    ))

    if not app:
        raise HTTPException(status_code=404, detail="Could not find application")

    app.is_active = False
    app.end_date = datetime.utcnow().date()

    await db.commit()
    await db.refresh(app)

    return SuccessResponse(status=True, detail="Success")
