"""Policy check node — validate action against safety policies."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.state import RecoveryState
from app.recovery.policy import RecoveryPolicy
from app.core.logging import get_logger

logger = get_logger("agent.policy")


async def policy_check(state: RecoveryState, session: AsyncSession) -> RecoveryState:
    """Validate the proposed action against recovery policies."""
    if state.get("next_step") == "finalize" or state.get("final_status") is not None:
        return state

    policy = RecoveryPolicy()

    payment_data = state.get("payment_data", {})
    action = state.get("action", "")

    # Get recovery attempt count
    from app.repositories.recovery_repository import RecoveryRepository
    recovery_repo = RecoveryRepository(session)
    recovery = await recovery_repo.get_active_for_payment(state.get("payment_id", 0))

    attempt_count = recovery.attempt_count if recovery else 0
    max_attempts = recovery.max_attempts if recovery else 3
    recovery_status = recovery.status if recovery else "pending"

    result = policy.validate(
        action=action,
        payment_status=payment_data.get("status", "unknown"),
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        recovery_status=recovery_status,
        parameters=state.get("action_parameters", {}),
    )

    state["policy_result"] = result.model_dump()

    if not result.allowed:
        # Policy blocked the action -> Escalate to human review
        state.update({
            "action": "ESCALATE_TO_SUPPORT",
            "requires_human_review": True,
            "human_review_reason": f"Policy check failed: {result.reason}",
            "explanation": f"[Human Review Required] Policy blocked automated action: {result.reason}.",
            "next_step": "finalize",
            "final_status": "escalated",
        })

    logger.info("policy_checked", action=action, allowed=result.allowed)

    return state