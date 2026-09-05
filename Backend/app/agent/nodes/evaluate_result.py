"""Evaluate result node — check if recovery was successful."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.state import RecoveryState
from app.core.logging import get_logger

logger = get_logger("agent.evaluate")


async def evaluate_result(state: RecoveryState, session: AsyncSession) -> RecoveryState:
    action_result = state.get("action_result", {})
    action = state.get("action", "")
    payment_data = state.get("payment_data", {})

    if action_result.get("status") in ("recovered", "captured", "authorized") or payment_data.get("status") in (
        "captured",
        "authorized",
    ):
        state.update({
            "next_step": "finalize",
            "final_status": "recovered",
            "explanation": "Payment has been recovered successfully.",
        })
        logger.info("payment_recovered_via_action", action=action)
        return state

    if action_result.get("error"):
        state["next_step"] = "adapt"
        logger.info("action_evaluated", action=action, next_step="adapt")
        return state

    if not state.get("operator_override") and (
        action == "ESCALATE_TO_SUPPORT"
        or state.get("requires_human_review")
        or state.get("strategy") in ("escalate", "low_recoverability")
    ):
        state.update({
            "next_step": "finalize",
            "final_status": "escalated",
            "explanation": state.get("explanation") or "Recovery escalated for human review.",
        })
    elif action == "STOP_RECOVERY":
        state.update({
            "next_step": "finalize",
            "final_status": "exhausted",
            "explanation": "Recovery stopped. All automated options exhausted.",
        })
    else:
        # One action per webhook. Wait for the next Razorpay event before continuing.
        state.update({
            "next_step": "finalize",
            "final_status": "observing",
            "next_action": action,
            "explanation": state.get("explanation")
            or f"Executed {action}. Waiting for the next payment webhook.",
        })

    logger.info("action_evaluated", action=action, next_step=state.get("next_step"), final_status=state.get("final_status"))
    return state
