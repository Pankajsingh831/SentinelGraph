import uuid
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

class User(Base):
    __tablename__ = 'users'
    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(128), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default='ANALYST')  # ANALYST or ADMIN
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
