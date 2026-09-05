"""Adapt strategy node — change strategy when actions fail."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.state import RecoveryState
from app.recovery.strategies import get_strategy_steps, get_next_step
from app.core.logging import get_logger

logger = get_logger("agent.adapt")


# Strategy adaptation map: what to switch to when current strategy fails
ADAPTATION_MAP: dict[str, str] = {
    "temporary_failure": "upi_failure",
    "upi_failure": "notify_alternative",
    "network_timeout": "notify_retry",
    "bank_decline": "notify_alternative",
    "notify_retry": "escalate",
    "notify_alternative": "escalate",
    "low_recoverability": "escalate",
}


async def adapt_strategy(state: RecoveryState, session: AsyncSession) -> RecoveryState:
    """Adapt the recovery strategy based on results."""
    current_strategy = state.get("strategy", "temporary_failure")
    previous_actions = state.get("previous_actions", [])
    payment_data = state.get("payment_data", {})

    # Check attempt count
    attempt_count = payment_data.get("attempt_count", 0)

    # Determine new strategy
    new_strategy = ADAPTATION_MAP.get(current_strategy, "escalate")

    # If too many attempts, always escalate or exhaust
    if attempt_count >= 3:
        new_strategy = "escalate"

    # Get new strategy steps
    steps = get_strategy_steps(new_strategy)
    next_step_info = steps[0] if steps else None

    if next_step_info:
        state.update({
            "strategy": new_strategy,
            "current_step": next_step_info["step"],
            "action": next_step_info["action"],
            "action_parameters": {k: v for k, v in next_step_info.items() if k not in ("step", "action")},
            "explanation": (
                f"The previous strategy ({current_strategy}) did not recover the payment. "
                f"Switching to {new_strategy} strategy. "
                f"Continuing identical retries has diminishing value, "
                f"so the agent is switching to an alternative recovery path."
            ),
        })
    else:
        state.update({
            "next_step": "finalize",
            "final_status": "exhausted",
            "explanation": "All recovery strategies exhausted. Escalating to support.",
        })

    logger.info("strategy_adapted", from_strategy=current_strategy, to_strategy=new_strategy)

    return state