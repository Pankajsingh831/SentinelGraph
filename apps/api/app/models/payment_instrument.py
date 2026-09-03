import uuid
from datetime import datetime
from sqlalchemy import String, CHAR, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class PaymentInstrument(Base):
    __tablename__ = 'payment_instruments'
    instrument_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instrument_type: Mapped[str] = mapped_column(String(32))
    issuer_country: Mapped[str | None] = mapped_column(CHAR(2))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
