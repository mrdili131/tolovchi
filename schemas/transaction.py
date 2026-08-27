from pydantic import BaseModel, Field, ConfigDict
from models import TransactionStatus
from schemas import UserResponse

class TransactionForm(BaseModel):
    amount: int = Field(ge=1000)
    card_id: int
    service_id: int

    model_config = {
        "from_attributes": True
    }


class TransactionResponse(BaseModel):
    id: int
    amount: int
    status: TransactionStatus
    sender_id: int
    receiver_id: int
    sender: UserResponse

    model_config = ConfigDict(from_attributes=True)