from pydantic import BaseModel
from typing import Generic, TypeVar

class SuccessResponse(BaseModel):
    status: bool
    detail: str


T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool