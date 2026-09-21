from fastapi import APIRouter, Depends, HTTPException, Request
from database import Session
from schemas import RegisterSchema, LoginResponse, UserResponse, ServiceResponse, ProfileUpdateForm, SuccessResponse, SessionResponse, PaginatedResponse
from services import (
    authenticate_user, issue_token, pwd_context, Annotated, OAuth2PasswordRequestForm,
    user_dependency, service_auth,
    PaginationParams, paginate,
)
from datetime import timedelta, datetime
from sqlalchemy import select
from models import User, UserSession

router = APIRouter()


@router.post('/register', response_model=SuccessResponse, status_code=201, summary="Register a new user account")
async def register(db: Session, form: RegisterSchema):
    user = await db.scalar(select(User).where(User.username==form.username))
    if user:
        raise HTTPException(status_code=409, detail="User with this username already exists")

    if form.password != form.password_confirm:
        raise HTTPException(status_code=400, detail="Passwords don't match")

    new_user = User(
        username = form.username,
        password_hash = pwd_context.hash(form.password),
        last_name = form.last_name,
        first_name = form.first_name,
        middle_name = form.middle_name,
        phone_number = form.phone_number
    )
    db.add(new_user)
    await db.commit()
    return SuccessResponse(status=True, detail="User has been created")


@router.post('/login', response_model=LoginResponse, status_code=200, summary="Log in and receive an access token")
async def login(db: Session, request: Request, form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await authenticate_user(form.username, form.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials, try again")

    token = await issue_token(db, user, timedelta(days=5), request)
    return LoginResponse(access_token=token,token_type="bearer", role=user.role)


@router.get('/me', response_model=UserResponse, status_code=200, summary="Get your own profile. ROLES: [USER, ADMIN]")
async def get_my_profile(db: Session, user: user_dependency):
    db_user = await db.scalar(select(User).where(User.id==user.get("id")))
    return db_user


@router.get('/me_service', response_model=ServiceResponse, status_code=200, summary="Get your own service profile. ROLES: [SERVICE]")
async def get_my_service_profile(db: Session, user: service_auth):
    db_user = await db.scalar(select(User).where(User.id==user.get("id")))
    return db_user


@router.patch('/me', response_model=UserResponse, status_code=200, summary="Edit your own profile (name/phone). None of these fields may be blank. ROLES: [USER, SERVICE, ADMIN]")
async def update_my_profile(db: Session, user: user_dependency, form: ProfileUpdateForm):
    db_user = await db.get(User, user.get("id"))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.last_name = form.last_name
    db_user.first_name = form.first_name
    db_user.middle_name = form.middle_name
    db_user.phone_number = form.phone_number

    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post('/sessions/revoke-all', response_model=SuccessResponse, status_code=200, summary="Log out every one of your own sessions, on every device (including this one). ROLES: [USER, SERVICE, ADMIN]")
async def revoke_all_my_sessions(db: Session, user: user_dependency):
    sessions = await db.scalars(select(UserSession).where(
        UserSession.user_id == user.get("id"),
        UserSession.revoked_at == None,
    ))
    now = datetime.utcnow()
    for session in sessions.all():
        session.revoked_at = now
    await db.commit()

    return SuccessResponse(status=True, detail="All sessions revoked")


@router.get('/sessions', response_model=PaginatedResponse[SessionResponse], status_code=200, summary="List your own active/past login sessions. ROLES: [USER, SERVICE, ADMIN]")
async def get_my_sessions(db: Session, user: user_dependency, params: PaginationParams):
    stmt = select(UserSession).where(UserSession.user_id == user.get("id")).order_by(UserSession.id.desc())
    return await paginate(db, stmt, params)


@router.post('/sessions/{session_id}/revoke', response_model=SuccessResponse, status_code=200, summary="Revoke one of your own sessions (log that device out). ROLES: [USER, SERVICE, ADMIN]")
async def revoke_my_session(db: Session, user: user_dependency, session_id: int):
    session = await db.scalar(select(UserSession).where(UserSession.id == session_id, UserSession.user_id == user.get("id")))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.revoked_at = datetime.utcnow()
    await db.commit()

    return SuccessResponse(status=True, detail="Session revoked")
