from pydantic import BaseModel, Field, field_validator
from schemas import UserResponse


class CardResponse(BaseModel):
    id: int
    holder: str | None = None
    pan: str | None = None
    expiry: str | None = None

    model_config = {
        "from_attributes": True
    }


class CardBindForm(BaseModel):
    card_number: str = Field(description="16 digits; spaces are ignored")
    expire_date: str = Field(description="MMYY, e.g. 0929 for 09/29; a slash is ignored")

    @field_validator("card_number")
    @classmethod
    def _card_number(cls, v: str) -> str:
        v = v.replace(" ", "").replace("-", "")
        if not (v.isdigit() and len(v) == 16):
            raise ValueError("Karta raqami 16 ta raqamdan iborat bo'lishi kerak")
        return v

    @field_validator("expire_date")
    @classmethod
    def _expire_date(cls, v: str) -> str:
        v = v.replace("/", "").replace(" ", "")
        if not (v.isdigit() and len(v) == 4 and 1 <= int(v[:2]) <= 12):
            raise ValueError("Amal qilish muddati MM/YY formatida bo'lishi kerak")
        return v


class CardBindResponse(BaseModel):
    card_id: int
    phone_masked: str | None = None
    wait_ms: int | None = None


class CardVerifyForm(BaseModel):
    card_id: int
    code: str = Field(min_length=1, max_length=12)


class AdminCardResponse(CardResponse):
    is_active: bool
    user_id: int | None = None
    user: UserResponse | None = None

    model_config = {
        "from_attributes": True
    }