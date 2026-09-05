from pydantic import BaseModel
from datetime import datetime
from app.schemas.payment import PaymentResponse


class RecoveryActionResponse(BaseModel):
    id: int
    action_type: str
    action_status: str
    reason: str | None = None
    parameters: str | None = None
    result: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class RecoveryResponse(BaseModel):
    id: int
    payment_id: int
    status: str
    root_cause: str | None = None
    root_cause_confidence: float | None = None
    recoverability_score: float | None = None
    current_strategy: str | None = None
    current_step: str | None = None
    attempt_count: int
    max_attempts: int
    next_action: str | None = None
    next_action_at: datetime | None = None
    recovered_at: datetime | None = None
    explanation: str | None = None
    created_at: datetime
    updated_at: datetime
    actions: list[RecoveryActionResponse] = []
    payment: PaymentResponse | None = None

    model_config = {"from_attributes": True}


class RecoveryListResponse(BaseModel):
    recoveries: list[RecoveryResponse]
    total: int


class RecoveryPauseResponse(BaseModel):
    recovery_id: int
    status: str
    message: str


class HumanReviewRequest(BaseModel):
    decision: str  # "approve_retry", "reject", "resolve"
    notes: str | None = None


class HumanReviewResponse(BaseModel):
    recovery_id: int
    status: str
    message: str

