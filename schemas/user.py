from pydantic import BaseModel, ConfigDict, Field
from models import UserType

NO_SPACES = r"^\S+$"

class RegisterSchema(BaseModel):
    username: str = Field(min_length=8,pattern=NO_SPACES)
    last_name: str
    first_name: str
    middle_name: str
    password: str = Field(min_length=8,pattern=NO_SPACES)
    password_confirm: str = Field(min_length=8,pattern=NO_SPACES)

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


class ServiceResponse(BaseModel):
    id: int
    username: str | None = None
    service_name: str | None = None
    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    role: UserType | None = None
    balance: int

    model_config = ConfigDict(from_attributes=True)