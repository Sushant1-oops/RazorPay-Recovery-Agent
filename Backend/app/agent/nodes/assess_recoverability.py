"""Assess recoverability node — compute recovery score."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.state import RecoveryState
from app.recovery.scoring import RecoveryScorer
from app.repositories.recovery_repository import RecoveryRepository
from app.core.logging import get_logger

logger = get_logger("agent.assess")


async def assess_recoverability(state: RecoveryState, session: AsyncSession) -> RecoveryState:
    scorer = RecoveryScorer()
    payment_data = state.get("payment_data", {})
    customer_data = state.get("customer_data", {})

    score = scorer.score(
        root_cause=state.get("root_cause", "unknown"),
        root_cause_confidence=state.get("root_cause_confidence", 0.0),
        attempt_count=payment_data.get("attempt_count", 0),
        payment_method=payment_data.get("payment_method"),
        amount=payment_data.get("amount", 0),
        customer_history=customer_data,
    )
    category = scorer.categorize(score)

    state.update({
        "recoverability_score": score,
        "recoverability_category": category,
    })

    if category == "low_recoverability":
        state["strategy"] = "low_recoverability"

    recovery_id = state.get("recovery_id")
    if recovery_id:
        recovery_repo = RecoveryRepository(session)
        recovery = await recovery_repo.get_by_id(recovery_id)
        if recovery:
            await recovery_repo.update(
                recovery,
                root_cause=state.get("root_cause"),
                root_cause_confidence=state.get("root_cause_confidence"),
                recoverability_score=score,
                current_strategy=state.get("strategy"),
                explanation=state.get("explanation"),
            )

    logger.info("recoverability_assessed", score=score, category=category)
    return state
