from pydantic import BaseModel, Field, ConfigDict
from models import TransactionStatus
from schemas import UserResponse, TransactionPartyResponse, ApplicationResponse
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
    fee_amount: int
    status: TransactionStatus
    created_at: date

    sender: UserResponse
    receiver: TransactionPartyResponse
    application: ApplicationResponse | None = None # Remove none on production db

    is_flagged: bool
    admin_note: str | None = None
    refunded_at: date | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminTransactionUpdateForm(BaseModel):
    is_flagged: bool | None = None
    admin_note: str | None = None
    mark_refunded: bool = False