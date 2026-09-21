from pydantic import BaseModel
from schemas import UserResponse


class CardResponse(BaseModel):
    id: int
    holder: str | None = None
    pan: str | None = None
    expiry: str | None = None

    model_config = {
        "from_attributes": True
    }


class CardBindResponse(BaseModel):
    card_link_url: str

    model_config = {
        "from_attributes": True
    }


class AdminCardResponse(CardResponse):
    is_active: bool
    user_id: int | None = None
    user: UserResponse | None = None

    model_config = {
        "from_attributes": True
    }