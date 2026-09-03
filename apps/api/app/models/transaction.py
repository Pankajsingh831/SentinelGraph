import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, CHAR, DateTime, NUMERIC, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class Transaction(Base):
    __tablename__ = 'transactions'
    transaction_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('customers.customer_id'))
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('merchants.merchant_id'))
    device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('devices.device_id'))
    instrument_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('payment_instruments.instrument_id'))
    ip_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('ip_addresses.ip_id'))
    amount: Mapped[Decimal] = mapped_column(NUMERIC(18, 2))
    currency: Mapped[str] = mapped_column(CHAR(3))
    transaction_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
