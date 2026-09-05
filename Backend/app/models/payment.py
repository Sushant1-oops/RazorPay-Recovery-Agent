from sqlalchemy import String, Integer, Boolean, DateTime, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base


class Payment(Base):
    __tablename__ = "payments"

    razorpay_payment_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="created", nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recovered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    events: Mapped[list["PaymentEvent"]] = relationship(back_populates="payment", lazy="selectin")
    recoveries: Mapped[list["Recovery"]] = relationship(back_populates="payment", lazy="selectin")