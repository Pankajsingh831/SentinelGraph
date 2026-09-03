from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: Optional[str] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int
