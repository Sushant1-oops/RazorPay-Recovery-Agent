from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base


class Recovery(Base):
    __tablename__ = "recoveries"

    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    root_cause: Mapped[str | None] = mapped_column(String(100), nullable=True)
    root_cause_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    recoverability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_strategy: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    payment: Mapped["Payment"] = relationship(back_populates="recoveries", lazy="selectin")
    actions: Mapped[list["RecoveryAction"]] = relationship(back_populates="recovery", lazy="selectin")