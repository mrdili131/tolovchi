from pydantic import BaseModel, Field
from models import PaymentFrequency
from schemas import UserResponse
from datetime import date

class ApplicationForm(BaseModel):
    name: str
    description: str
    amount: int = Field(ge=1000)
    frequency: PaymentFrequency
    pay_day: int


class ApplicationResponse(BaseModel):
    id: int
    name: str
    description: str
    cancellable: bool
    frequency: PaymentFrequency
    start_date: date
    end_date: date | None = None
    pay_day: int
    balance: int
    debt: int
    is_active: bool

    payer: UserResponse | None = None
    service: UserResponse | None = None

    model_config = {
        "from_attributes": True
    }