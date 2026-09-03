import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, DOUBLE_PRECISION
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class RiskCase(Base):
    __tablename__ = 'risk_cases'
    case_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    primary_entity_type: Mapped[str] = mapped_column(String(32))
    primary_entity_id: Mapped[uuid.UUID] = mapped_column()
    transaction_risk_score: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    network_risk_score: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    temporal_risk_score: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    overall_risk_score: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    risk_tier: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default='open')
    case_reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
