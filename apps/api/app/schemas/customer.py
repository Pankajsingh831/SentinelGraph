from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime
from typing import Optional

class CustomerResponse(BaseModel):
    customer_id: uuid.UUID
    country: Optional[str] = None
    status: str
    account_created_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
