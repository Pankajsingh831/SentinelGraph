import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, DOUBLE_PRECISION
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class NetworkRisk(Base):
    __tablename__ = 'network_risks'
    network_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    node_count: Mapped[int] = mapped_column(Integer)
    edge_count: Mapped[int] = mapped_column(Integer)
    network_density: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    community_id: Mapped[str | None] = mapped_column(String(128))
    graph_risk_score: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
