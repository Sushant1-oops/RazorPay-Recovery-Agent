"""Finalize recovery node — update database with final state."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.state import RecoveryState
from app.repositories.recovery_repository import RecoveryRepository
from app.repositories.payment_repository import PaymentRepository
from app.core.logging import get_logger
from datetime import datetime, timezone

logger = get_logger("agent.finalize")


async def finalize_recovery(state: RecoveryState, session: AsyncSession) -> RecoveryState:
    """Update recovery and payment records with final status."""
    recovery_repo = RecoveryRepository(session)
    payment_repo = PaymentRepository(session)

    recovery = await recovery_repo.get_active_for_payment(state.get("payment_id", 0))
    if not recovery:
        return state

    final_status = state.get("final_status", "exhausted")
    explanation = state.get("explanation", "")

    update_data = {
        "status": final_status,
        "root_cause": state.get("root_cause"),
        "root_cause_confidence": state.get("root_cause_confidence"),
        "recoverability_score": state.get("recoverability_score"),
        "current_strategy": state.get("strategy"),
        "current_step": state.get("current_step"),
        "explanation": explanation,
        "next_action": None,
    }

    if final_status == "recovered":
        update_data["recovered_at"] = datetime.now(timezone.utc)
        # Mark payment as recovered
        payment = await payment_repo.get_by_id(state.get("payment_id", 0))
        if payment:
            await payment_repo.update(payment, recovered=True, status="captured")

    await recovery_repo.update(recovery, **update_data)

    # Audit log
    await recovery_repo.add_audit(
        recovery_id=recovery.id,
        event_type="recovery_finalized",
        actor="agent",
        action=f"finalize_{final_status}",
        metadata_={"final_status": final_status, "explanation": explanation},
    )

    logger.info("recovery_finalized", recovery_id=recovery.id, final_status=final_status)

    return state