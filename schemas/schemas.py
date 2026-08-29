from pydantic import BaseModel

class SuccessResponse(BaseModel):
    status: bool
    detail: str