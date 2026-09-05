from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    recovery_id: Mapped[int | None] = mapped_column(ForeignKey("recoveries.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)