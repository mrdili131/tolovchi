from fastapi import APIRouter, Depends, HTTPException
from database import Session
from schemas import RegisterSchema, LoginResponse
from services import  authenticate_user, create_token, pwd_context, Annotated, OAuth2PasswordRequestForm
from datetime import timedelta
from sqlalchemy import select
from models import User

router = APIRouter()


@router.post('/register',status_code=201)
async def register(db: Session, form: RegisterSchema):
    user = await db.scalar(select(User).where(User.username==form.username))
    if user:
         return HTTPException(status_code=204,detail="User with this username exist")
    
    if form.password == form.password_confirm:
        new_user = User(
            username = form.username,
            password_hash = pwd_context.hash(form.password),
            service_name = form.username,
        )
        db.add(new_user)
        await db.commit()
        return {"status":True,"msg":"User has been created"}
    else:
        return {"status":False,"msg":"Passwords don't match"}

    

@router.post('/login', response_model=LoginResponse, status_code=200)
async def login(db: Session, form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await authenticate_user(form.username, form.password, db)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid credentials, try again")

    token = create_token(user.username,user.id,user.type,timedelta(days=5))
    return LoginResponse(access_token=token,token_type="bearer")