from fastapi import Depends, HTTPException
from models import User, UserType
from sqlalchemy import select
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from dotenv import load_dotenv
import os
from datetime import timedelta, datetime, timezone
from typing import Annotated


load_dotenv()



SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")


async def authenticate_user(username,password,db):
    user = await db.scalar(select(User).where(User.username==username))
    if not user:
        return False
    if not pwd_context.verify(password,user.password_hash):
        return False
    return user
        

def create_token(username: str, user_id: int, user_type: UserType, expires_delta: timedelta):
    encode = {'username':username,'user_id':user_id,'role':user_type.value}
    expire = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp':expire})
    return jwt.encode(encode,SECRET_KEY,algorithm=ALGORITHM)

async def get_user(token: Annotated[str,Depends(oauth2_scheme)]):
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
        if username is None or user_id is None:
            raise exception_err
        return {"username":username,"id":user_id,"role":role,"token":token,"type":"bearer"}
    except JWTError:
        raise exception_err
    


# Role based dependency
async def service_required(user: user_dependency):
    if user.get("role") != UserType.SERVICE.value:
        raise HTTPException(status_code=403, detail="User role should be service")
    return user


async def user_required(user: user_dependency):
    if user.get("role") != UserType.USER.value:
        raise HTTPException(status_code=403, detail="User role should be user")
    return user


user_dependency = Annotated[dict,Depends(get_user)] # For Authorized account view
service_role = Annotated[dict, Depends(service_required)] # For Service account view
user_role = Annotated[dict, Depends(user_required)] # For User account view