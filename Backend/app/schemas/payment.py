from pydantic import BaseModel
from datetime import datetime


class PaymentResponse(BaseModel):
    id: int
    razorpay_payment_id: str
    razorpay_order_id: str | None = None
    customer_id: int | None = None
    amount: int
    currency: str
    payment_method: str | None = None
    status: str
    failure_code: str | None = None
    failure_reason: str | None = None
    attempt_count: int
    recovered: bool
    created_at: datetime
    updated_at: datetime
    recovery_id: int | None = None

    model_config = {"from_attributes": True}


class PaymentListResponse(BaseModel):
    payments: list[PaymentResponse]
    total: int