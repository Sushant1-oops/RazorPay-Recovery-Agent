"""Recovery strategy definitions and execution logic."""
from app.core.logging import get_logger
from enum import Enum

logger = get_logger("strategies")


class StrategyName(str, Enum):
    TEMPORARY_FAILURE = "temporary_failure"
    UPI_FAILURE = "upi_failure"
    BANK_DECLINE = "bank_decline"
    NETWORK_TIMEOUT = "network_timeout"
    NOTIFY_RETRY = "notify_retry"
    NOTIFY_ALTERNATIVE = "notify_alternative"
    ESCALATE = "escalate"
    LOW_RECOVERABILITY = "low_recoverability"


STRATEGY_STEPS: dict[str, list[dict]] = {
    StrategyName.TEMPORARY_FAILURE: [
        {"step": "wait", "action": "CHECK_PAYMENT_STATUS", "delay_seconds": 30},
        {"step": "retry", "action": "RETRY_PAYMENT_FLOW"},
        {"step": "observe", "action": "WAIT_FOR_EVENT"},
    ],
    StrategyName.UPI_FAILURE: [
        {"step": "wait", "action": "CHECK_PAYMENT_STATUS", "delay_seconds": 20},
        {"step": "retry", "action": "RETRY_PAYMENT_FLOW"},
        {"step": "alternative", "action": "OFFER_ALTERNATIVE_PAYMENT"},
    ],
    StrategyName.BANK_DECLINE: [
        {"step": "notify", "action": "SEND_NOTIFICATION", "template": "bank_declined"},
        {"step": "alternative", "action": "OFFER_ALTERNATIVE_PAYMENT"},
    ],
    StrategyName.NETWORK_TIMEOUT: [
        {"step": "wait", "action": "CHECK_PAYMENT_STATUS", "delay_seconds": 45},
        {"step": "safe_retry", "action": "RETRY_PAYMENT_FLOW"},
    ],
    StrategyName.NOTIFY_RETRY: [
        {"step": "notify", "action": "SEND_NOTIFICATION", "template": "retry_payment"},
        {"step": "wait", "action": "WAIT_FOR_EVENT"},
    ],
    StrategyName.NOTIFY_ALTERNATIVE: [
        {"step": "notify", "action": "SEND_NOTIFICATION", "template": "alternative_method"},
        {"step": "alternative", "action": "OFFER_ALTERNATIVE_PAYMENT"},
    ],
    StrategyName.ESCALATE: [
        {"step": "notify", "action": "SEND_NOTIFICATION", "template": "escalation"},
        {"step": "escalate", "action": "ESCALATE_TO_SUPPORT"},
    ],
    StrategyName.LOW_RECOVERABILITY: [
        {"step": "notify", "action": "SEND_NOTIFICATION", "template": "recovery_unlikely"},
        {"step": "escalate", "action": "ESCALATE_TO_SUPPORT"},
        {"step": "stop", "action": "STOP_RECOVERY"},
    ],
}


def get_strategy_steps(strategy_name: str) -> list[dict]:
    """Get the steps for a strategy."""
    return STRATEGY_STEPS.get(strategy_name, STRATEGY_STEPS[StrategyName.ESCALATE])


def get_next_step(strategy_name: str, current_step: str | None = None) -> dict | None:
    """Get the next step in a strategy after the current step."""
    steps = get_strategy_steps(strategy_name)
    if current_step is None:
        return steps[0] if steps else None
    for i, step in enumerate(steps):
        if step["step"] == current_step and i + 1 < len(steps):
            return steps[i + 1]
    return None