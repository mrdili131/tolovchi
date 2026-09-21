from pydantic import BaseModel, Field, ConfigDict, field_validator
from models import PayoutStatus
from schemas import UserResponse
from datetime import date


CARD_NUMBER_PATTERN = r"^\d{16}$"


class PayoutCreateForm(BaseModel):
    amount: int
    card_number: str = Field(pattern=CARD_NUMBER_PATTERN)

    @field_validator("card_number", mode="before")
    @classmethod
    def strip_spaces(cls, value):
        return value.replace(" ", "") if isinstance(value, str) else value


class PayoutResponse(BaseModel):
    id: int
    amount: int
    card_number: str
    status: str
    admin_note: str | None = None
    processed_at: date | None = None
    created_at: date | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminPayoutResponse(PayoutResponse):
    service: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class PayoutRejectForm(BaseModel):
    admin_note: str | None = None
