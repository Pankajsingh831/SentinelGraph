import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class EntityRelationship(Base):
    __tablename__ = 'entity_relationships'
    relationship_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[uuid.UUID] = mapped_column()
    relationship_type: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(32))
    target_id: Mapped[uuid.UUID] = mapped_column()
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    interaction_count: Mapped[int] = mapped_column(BigInteger, default=1)
