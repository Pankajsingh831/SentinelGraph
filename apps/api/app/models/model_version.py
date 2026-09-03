from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, BigInteger, NUMERIC, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class ModelVersion(Base):
    __tablename__ = 'model_versions'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(50))
    model_type: Mapped[str | None] = mapped_column(String(50))
    training_dataset: Mapped[str | None] = mapped_column(String(255))
    precision_score: Mapped[Decimal | None] = mapped_column(NUMERIC(8, 6))
    recall_score: Mapped[Decimal | None] = mapped_column(NUMERIC(8, 6))
    f1_score: Mapped[Decimal | None] = mapped_column(NUMERIC(8, 6))
    pr_auc: Mapped[Decimal | None] = mapped_column(NUMERIC(8, 6))
    threshold: Mapped[Decimal | None] = mapped_column(NUMERIC(8, 6))
    artifact_uri: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
