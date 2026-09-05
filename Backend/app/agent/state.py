"""Recovery agent state definition."""
from typing import TypedDict, Any


class RecoveryState(TypedDict, total=False):
    payment_id: int
    recovery_id: int
    payment_data: dict
    customer_data: dict
    recent_events: list[dict]
    failure_reason: str
    failure_code: str
    root_cause: str
    root_cause_confidence: float
    recoverability_score: float
    recoverability_category: str
    previous_actions: list[dict]
    strategy: str
    current_step: str
    action: str
    action_parameters: dict
    policy_result: dict
    action_result: dict
    next_step: str
    final_status: str
    explanation: str
    requires_human_review: bool
    human_review_reason: str
    operator_override: bool
    error: str