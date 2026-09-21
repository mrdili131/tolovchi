from pydantic import BaseModel, ConfigDict, Field
from datetime import date
from models import UserType

NO_SPACES = r"^\S+$"
PHONE_PATTERN = r"^998\d{9}$"

class RegisterSchema(BaseModel):
    username: str = Field(min_length=8,pattern=NO_SPACES)
    last_name: str
    first_name: str
    middle_name: str
    phone_number: str = Field(pattern=PHONE_PATTERN)
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
    phone_number: str | None = None
    role: UserType | None = None

    model_config = ConfigDict(from_attributes=True)


class ServiceResponse(BaseModel):
    id: int
    username: str | None = None
    service_name: str | None = None
    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    phone_number: str | None = None
    webhook_url: str | None = None
    role: UserType | None = None
    balance: int

    model_config = ConfigDict(from_attributes=True)


class TransactionPartyResponse(BaseModel):
    """Minimal public-facing identity for a transaction counterparty — avoids
    leaking a service's balance/webhook_url to the customer on the other side."""
    id: int
    username: str | None = None
    service_name: str | None = None
    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    role: UserType | None = None

    model_config = ConfigDict(from_attributes=True)


class UserAdminResponse(BaseModel):
    id: int
    username: str | None = None
    service_name: str | None = None
    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    phone_number: str | None = None
    role: UserType | None = None
    balance: int
    is_active: bool
    created_at: date | None = None

    model_config = ConfigDict(from_attributes=True)


class RoleUpdateForm(BaseModel):
    role: UserType


class StatusUpdateForm(BaseModel):
    is_active: bool


class AdminUserUpdateForm(BaseModel):
    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    phone_number: str | None = Field(default=None, pattern=PHONE_PATTERN)
    service_name: str | None = None


class ProfileUpdateForm(BaseModel):
    """Self-service profile edit. All fields required and non-empty — a
    profile can never be left with a blank name or phone number."""
    last_name: str = Field(min_length=1)
    first_name: str = Field(min_length=1)
    middle_name: str = Field(min_length=1)
    phone_number: str = Field(pattern=PHONE_PATTERN)


class WebhookUpdateForm(BaseModel):
    webhook_url: str | None = Field(default=None, max_length=500)