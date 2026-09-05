"""Analyze failure node — classify root cause using LLM + deterministic rules."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.state import RecoveryState
from app.recovery.classifier import FailureClassifier
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger("agent.analyze")


async def analyze_failure(state: RecoveryState, session: AsyncSession) -> RecoveryState:
    classifier = FailureClassifier()
    payment_data = state.get("payment_data", {})
    customer_data = state.get("customer_data", {})

    root_cause_result = None
    if settings.GROQ_API_KEY:
        try:
            root_cause_result = await _llm_analyze(state)
        except Exception as e:
            logger.warning("llm_analysis_failed_falling_back", error=str(e))

    if root_cause_result is None:
        root_cause_result = classifier.classify(
            failure_code=state.get("failure_code"),
            failure_reason=state.get("failure_reason"),
            payment_method=payment_data.get("payment_method"),
            amount=payment_data.get("amount", 0),
            attempt_count=payment_data.get("attempt_count", 0),
            customer_history=customer_data,
        )

    existing_step = (state.get("current_step") or "").strip()
    state.update({
        "root_cause": root_cause_result.root_cause,
        "root_cause_confidence": root_cause_result.confidence,
        "explanation": root_cause_result.reason,
    })
    if not existing_step:
        state["strategy"] = root_cause_result.recommended_strategy

    logger.info(
        "root_cause_detected",
        root_cause=root_cause_result.root_cause,
        confidence=root_cause_result.confidence,
        recoverable=root_cause_result.recoverable,
    )
    return state


async def _llm_analyze(state: RecoveryState):
    from app.agent.tools.payment_tools import analyze_failure_with_llm

    return await analyze_failure_with_llm(state)
