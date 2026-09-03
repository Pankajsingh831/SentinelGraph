import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, DOUBLE_PRECISION
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class TemporalAnomaly(Base):
    __tablename__ = 'temporal_anomalies'
    anomaly_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[uuid.UUID] = mapped_column()
    anomaly_type: Mapped[str] = mapped_column(String(64))
    baseline_value: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    observed_value: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    anomaly_score: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
