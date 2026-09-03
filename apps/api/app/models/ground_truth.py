import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class GroundTruth(Base):
    __tablename__ = 'ground_truth'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID] = mapped_column()
    scenario_id: Mapped[str | None] = mapped_column(String(128))
    is_abuse: Mapped[bool] = mapped_column(Boolean)
    abuse_type: Mapped[str | None] = mapped_column(String(100))
    injected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
