from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class NotificationCreateForm(BaseModel):
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)
    target_user_id: int | None = None  # None = broadcast to everyone


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    target_user_id: int | None = None
    created_at: datetime | None = None
    is_read: bool = False

    model_config = ConfigDict(from_attributes=True)
