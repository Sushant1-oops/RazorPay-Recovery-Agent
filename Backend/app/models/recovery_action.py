from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    recovery_id: Mapped[int] = mapped_column(ForeignKey("recoveries.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    parameters: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    recovery: Mapped["Recovery"] = relationship(back_populates="actions", lazy="selectin")