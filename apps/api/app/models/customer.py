import uuid
from datetime import datetime
from sqlalchemy import String, CHAR, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class Customer(Base):
    __tablename__ = 'customers'
    customer_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    country: Mapped[str | None] = mapped_column(CHAR(2))
    status: Mapped[str] = mapped_column(String(32), default='active')
    account_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
