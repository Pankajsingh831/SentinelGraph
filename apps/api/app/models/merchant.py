import uuid
from datetime import datetime
from sqlalchemy import String, CHAR, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class Merchant(Base):
    __tablename__ = 'merchants'
    merchant_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    merchant_name: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(64))
    country: Mapped[str | None] = mapped_column(CHAR(2))
    status: Mapped[str] = mapped_column(String(32), default='active')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
