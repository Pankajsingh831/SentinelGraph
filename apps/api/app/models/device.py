import uuid
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class Device(Base):
    __tablename__ = 'devices'
    device_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_type: Mapped[str | None] = mapped_column(String(32))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
