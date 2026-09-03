from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

class TransactionResponse(BaseModel):
    transaction_id: uuid.UUID
    customer_id: uuid.UUID
    merchant_id: uuid.UUID
    device_id: Optional[uuid.UUID] = None
    instrument_id: Optional[uuid.UUID] = None
    ip_id: Optional[uuid.UUID] = None
    amount: Decimal
    currency: str
    transaction_type: str
    status: str
    occurred_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
