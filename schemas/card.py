from pydantic import BaseModel


class CardResponse(BaseModel):
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