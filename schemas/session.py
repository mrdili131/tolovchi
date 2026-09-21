from pydantic import BaseModel, ConfigDict
from datetime import datetime
from schemas import UserResponse


class SessionResponse(BaseModel):
    id: int
    user_id: int | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    expires_at: datetime
    last_seen_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminSessionResponse(SessionResponse):
    user: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)
