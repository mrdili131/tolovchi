from pydantic import BaseModel
from models import PaymentFrequency

class ApplicationResponse(BaseModel):
    id: int
    description: str
    cancellable: bool
    frequency: PaymentFrequency
    pay_day: int
    is_active: bool
    service_id: int
    payer_id: int

    model_config = {
        "from_attributes": True
    }