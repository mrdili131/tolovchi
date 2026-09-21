from pydantic import BaseModel, ConfigDict
from datetime import date


class ApiKeyCreateForm(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    id: int
    name: str | None = None
    key_prefix: str
    is_active: bool
    last_used_at: date | None = None
    revoked_at: date | None = None
    created_at: date | None = None

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreateResponse(ApiKeyResponse):
    key: str
