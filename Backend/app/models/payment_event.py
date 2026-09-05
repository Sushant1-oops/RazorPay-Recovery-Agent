from sqlalchemy import String, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (UniqueConstraint("event_id", name="uq_payment_event_event_id"),)

    event_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    razorpay_payment_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    signature: Mapped[str | None] = mapped_column(String(512), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), nullable=True)
    payment: Mapped["Payment | None"] = relationship(back_populates="events", lazy="selectin")