from pydantic import BaseModel, ConfigDict
from datetime import datetime


class PaymentAttemptResponse(BaseModel):
    id: int
    application_id: int | None = None
    success: bool
    reason: str | None = None
    attempt_number: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
