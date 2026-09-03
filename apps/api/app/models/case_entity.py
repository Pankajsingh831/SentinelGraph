import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class CaseEntity(Base):
    __tablename__ = 'case_entities'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('risk_cases.case_id', ondelete='CASCADE'))
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[uuid.UUID] = mapped_column()
    role: Mapped[str | None] = mapped_column(String(50))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
