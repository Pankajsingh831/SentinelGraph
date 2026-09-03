import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Integer, DOUBLE_PRECISION, NUMERIC
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class RiskFeature(Base):
    __tablename__ = 'risk_features'
    feature_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[uuid.UUID] = mapped_column()
    transaction_count_5m: Mapped[int | None] = mapped_column(Integer)
    transaction_count_1h: Mapped[int | None] = mapped_column(Integer)
    transaction_count_24h: Mapped[int | None] = mapped_column(Integer)
    avg_transaction_amount: Mapped[Decimal | None] = mapped_column(NUMERIC(18, 2))
    refund_rate: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    account_age_hours: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    device_account_count: Mapped[int | None] = mapped_column(Integer)
    ip_account_count: Mapped[int | None] = mapped_column(Integer)
    merchant_connection_count: Mapped[int | None] = mapped_column(Integer)
    network_size: Mapped[int | None] = mapped_column(Integer)
    network_density: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    network_growth_rate: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
