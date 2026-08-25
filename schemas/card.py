from pydantic import BaseModel


class CardResponse(BaseModel):
    id: int
    pan: str
    expiry: str
    is_active: bool

    model_config = {
        "from_attributes": True
    }


class CardBindResponse(BaseModel):
    card_link_url: str

    model_config = {
        "from_attributes": True
    }