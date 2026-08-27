from pydantic import BaseModel, Field
from models import TransactionStatus

class TransactionForm(BaseModel):
    amount: int = Field(ge=1000)
    card_id: int
    service_id: int

    model_config = {
        "from_attributes": True
    }


class TransactionResponse(BaseModel):
    amount: int
    status: TransactionStatus
    sender_id: int
    receiver_id: int

    model_config = {
        "from_attributes": True
    }