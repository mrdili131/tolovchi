from pydantic import BaseModel, ConfigDict
from datetime import datetime


class AuditLogResponse(BaseModel):
    id: int
    admin_id: int | None = None
    action: str
    target_type: str
    target_id: int
    detail: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
