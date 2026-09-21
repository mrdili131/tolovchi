from fastapi import Depends, HTTPException, Request
from models import User, UserType, UserSession
from sqlalchemy import select
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer, APIKeyHeader
from dotenv import load_dotenv
import os
import secrets
from datetime import timedelta, datetime, timezone
from typing import Annotated
from database import Session
from services.api_key_service import get_service_by_api_key


load_dotenv()



SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)

pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")


async def authenticate_user(username,password,db):
    user = await db.scalar(select(User).where(User.username==username))
    if not user:
        return False
    if not pwd_context.verify(password,user.password_hash):
        return False
    if not user.is_active:
        return False
    return user


def create_token(username: str, user_id: int, user_type: UserType, expires_delta: timedelta, jti: str):
    encode = {'username':username,'user_id':user_id,'role':user_type.value,'jti':jti}
    expire = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp':expire})
    return jwt.encode(encode,SECRET_KEY,algorithm=ALGORITHM)


async def issue_token(db, user: User, expires_delta: timedelta, request: Request | None = None) -> str:
    jti = secrets.token_hex(16)
    expires_at = datetime.utcnow() + expires_delta

    session = UserSession(
        user_id=user.id,
        jti=jti,
        user_agent=request.headers.get("user-agent") if request else None,
        ip_address=request.client.host if request and request.client else None,
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()

    return create_token(user.username, user.id, user.role, expires_delta, jti)


async def get_user(token: Annotated[str,Depends(oauth2_scheme)], db: Session):
    exception_err = HTTPException(
        status_code=401,
        detail='User is not authenticated',
        headers={"WWW-Authenticate":"Bearer"}
    )
    try:
        data = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        username = data.get('username')
        user_id = data.get('user_id')
        role = data.get('role')
        jti = data.get('jti')
        if username is None or user_id is None:
            raise exception_err

        db_user = await db.get(User, user_id)
        if not db_user or not db_user.is_active:
            raise exception_err

        if jti:
            session = await db.scalar(select(UserSession).where(UserSession.jti == jti))
            if not session or session.revoked_at is not None:
                raise exception_err
            session.last_seen_at = datetime.utcnow()
            await db.commit()

        return {"username":username,"id":user_id,"role":role,"token":token,"type":"bearer"}
    except JWTError:
        raise exception_err



# Role based dependency
async def admin_required(user: user_dependency):
    if user.get("role") != UserType.ADMIN.value:
        raise HTTPException(status_code=403, detail="User role should be admin")
    return user

async def service_required(user: user_dependency):
    if user.get("role") != UserType.SERVICE.value:
        raise HTTPException(status_code=403, detail="User role should be service")
    return user


async def user_required(user: user_dependency):
    if user.get("role") != UserType.USER.value:
        raise HTTPException(status_code=403, detail="User role should be user")
    return user


async def get_service_auth(
    db: Session,
    api_key: Annotated[str | None, Depends(api_key_scheme)] = None,
    token: Annotated[str | None, Depends(oauth2_scheme_optional)] = None,
):
    if api_key:
        db_key = await get_service_by_api_key(api_key, db)
        if not db_key:
            raise HTTPException(status_code=401, detail="Invalid API key")

        service_user = await db.get(User, db_key.service_id)
        if not service_user or not service_user.is_active or service_user.role != UserType.SERVICE:
            raise HTTPException(status_code=401, detail="Invalid API key")

        return {"username": service_user.username, "id": service_user.id, "role": UserType.SERVICE.value, "token": api_key, "type": "api_key"}

    if token:
        user = await get_user(token, db)
        if user.get("role") != UserType.SERVICE.value:
            raise HTTPException(status_code=403, detail="User role should be service")
        return user

    raise HTTPException(
        status_code=401,
        detail="Not authenticated. Provide a Bearer token or an X-API-Key header",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_flexible_auth(
    db: Session,
    api_key: Annotated[str | None, Depends(api_key_scheme)] = None,
    token: Annotated[str | None, Depends(oauth2_scheme_optional)] = None,
):
    """Resolves either a service's API key, or any role's Bearer JWT. Used on
    endpoints shared by users and services where a service should also be able
    to integrate via API key instead of logging in through the browser."""
    if api_key:
        db_key = await get_service_by_api_key(api_key, db)
        if not db_key:
            raise HTTPException(status_code=401, detail="Invalid API key")

        service_user = await db.get(User, db_key.service_id)
        if not service_user or not service_user.is_active or service_user.role != UserType.SERVICE:
            raise HTTPException(status_code=401, detail="Invalid API key")

        return {"username": service_user.username, "id": service_user.id, "role": UserType.SERVICE.value, "token": api_key, "type": "api_key"}

    if token:
        return await get_user(token, db)

    raise HTTPException(
        status_code=401,
        detail="Not authenticated. Provide a Bearer token or an X-API-Key header",
        headers={"WWW-Authenticate": "Bearer"},
    )


user_dependency = Annotated[dict,Depends(get_user)] # For Authorized account view
service_role = Annotated[dict, Depends(service_required)] # For Service account view
user_role = Annotated[dict, Depends(user_required)] # For User account view
admin_role = Annotated[dict,Depends(admin_required)] # For Authorized account view
service_auth = Annotated[dict, Depends(get_service_auth)] # For Service account view via JWT OR API key
flexible_auth = Annotated[dict, Depends(get_flexible_auth)] # For User OR Service view via JWT (either role) OR a Service's API key
