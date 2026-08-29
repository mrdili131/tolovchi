from pydantic import BaseModel, Field
from models import PaymentFrequency

class ApplicationForm(BaseModel):
    name: str
    description: str
    amount: int = Field(ge=1000)
    frequency: PaymentFrequency
    pay_day: int

class ApplicationResponse(BaseModel):
    id: int
    description: str
    cancellable: bool
    frequency: PaymentFrequency
    pay_day: int
    balance: int
    debt: int
    is_active: bool
    service_id: int
    payer_id: int | None = None

    model_config = {
        "from_attributes": True
    }