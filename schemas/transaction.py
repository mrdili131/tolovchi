from pydantic import BaseModel, Field, ConfigDict
from models import TransactionStatus
from schemas import UserResponse, ApplicationResponse
from datetime import date

class TransactionForm(BaseModel):
    amount: int = Field(ge=1000)
    application_id: int

    model_config = {
        "from_attributes": True
    }


class TransactionResponse(BaseModel):
    id: int
    amount: int
    status: TransactionStatus
    created_at: date

    sender: UserResponse
    receiver: UserResponse
    application: ApplicationResponse | None = None # Remove none on production db

    model_config = ConfigDict(from_attributes=True)