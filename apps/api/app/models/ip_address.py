import uuid
from datetime import datetime
from sqlalchemy import String, CHAR, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class IPAddress(Base):
    __tablename__ = 'ip_addresses'
    ip_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ip_hash: Mapped[str] = mapped_column(Text, unique=True)
    country: Mapped[str | None] = mapped_column(CHAR(2))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
