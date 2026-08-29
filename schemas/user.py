from pydantic import BaseModel, ConfigDict
from models import UserType

class RegisterSchema(BaseModel):
    username: str
    password: str
    password_confirm: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: UserType

class UserResponse(BaseModel):
    id: int
    username: str | None = None
    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    role: UserType | None = None

    model_config = ConfigDict(from_attributes=True)