import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, DOUBLE_PRECISION, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class RiskPrediction(Base):
    __tablename__ = 'risk_predictions'
    prediction_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('transactions.transaction_id'))
    model_version: Mapped[str] = mapped_column(String(64))
    risk_score: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    risk_tier: Mapped[str] = mapped_column(String(16))
    prediction_latency_ms: Mapped[int | None] = mapped_column(Integer)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
