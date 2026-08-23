from pydantic import BaseModel

class RegisterSchema(BaseModel):
    username: str
    password: str
    password_confirm: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str