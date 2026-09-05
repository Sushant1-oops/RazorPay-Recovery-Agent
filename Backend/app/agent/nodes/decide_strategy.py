"""Decide strategy node — select recovery strategy."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.state import RecoveryState
from app.recovery.strategies import get_strategy_steps, get_next_step
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger("agent.decide")


async def decide_strategy(state: RecoveryState, session: AsyncSession) -> RecoveryState:
    payment_data = state.get("payment_data", {})
    root_cause = state.get("root_cause", "unknown")
    confidence = state.get("root_cause_confidence", 0.0) or 0.0
    score = state.get("recoverability_score", 50.0) or 50.0
    amount = payment_data.get("amount", 0) or 0
    is_override = state.get("operator_override", False)

    # 1. RISK & AMBIGUITY GATE (Human Review Workflow)
    if not is_override:
        # High risk / fraud signals
        if root_cause == "suspected_risk":
            reason = "High risk / suspected fraud flag detected. Automated retries blocked."
            state.update({
                "strategy": "escalate",
                "requires_human_review": True,
                "human_review_reason": reason,
                "current_step": "escalate",
                "action": "ESCALATE_TO_SUPPORT",
                "action_parameters": {"reason": reason},
                "explanation": f"[Human Review Required] {reason}",
            })
            logger.info("strategy_escalated_high_risk", payment_id=state.get("payment_id"), reason=reason)
            return state

        # High Ambiguity: low confidence or unknown failure reason or high transaction value (>= 20,000 INR)
        if confidence < 0.60 or root_cause in ("unknown", "unspecified") or amount >= 2000000:
            reasons = []
            if confidence < 0.60:
                reasons.append(f"low AI confidence ({round(confidence * 100)}%)")
            if root_cause in ("unknown", "unspecified"):
                reasons.append("unclear/unknown failure reason")
            if amount >= 2000000:
                reasons.append(f"high transaction amount (INR {amount / 100:,.2f})")
            
            reason = f"Ambiguous failure: {', '.join(reasons)}."
            state.update({
                "strategy": "escalate",
                "requires_human_review": True,
                "human_review_reason": reason,
                "current_step": "escalate",
                "action": "ESCALATE_TO_SUPPORT",
                "action_parameters": {"reason": reason},
                "explanation": f"[Human Review Required] {reason}",
            })
            logger.info("strategy_escalated_ambiguous", payment_id=state.get("payment_id"), reason=reason)
            return state

        # Low recoverability: hard declines or exhausted probability
        if score < 30.0 or state.get("recoverability_category") == "low_recoverability":
            reason = f"Low recoverability score ({score}/100) for {root_cause}. Automated retry unlikely to succeed."
            state.update({
                "strategy": "low_recoverability",
                "requires_human_review": True,
                "human_review_reason": reason,
                "current_step": "escalate",
                "action": "ESCALATE_TO_SUPPORT",
                "action_parameters": {"reason": reason},
                "explanation": f"[Human Review Required] {reason}",
            })
            logger.info("strategy_escalated_low_recoverability", payment_id=state.get("payment_id"), reason=reason)
            return state

    # 2. AUTONOMOUS FLOW (Low Risk & High Confidence)
    strategy = state.get("strategy") or "temporary_failure"

    if settings.GROQ_API_KEY and not state.get("current_step"):
        try:
            llm_strategy = await _llm_decide_strategy(state)
            if llm_strategy:
                strategy = llm_strategy
        except Exception as e:
            logger.warning("llm_strategy_failed_using_deterministic", error=str(e))

    steps = get_strategy_steps(strategy)
    current_step = state.get("current_step") or None

    if current_step:
        next_step_info = get_next_step(strategy, current_step)
    else:
        next_step_info = steps[0] if steps else None

    if next_step_info:
        state.update({
            "strategy": strategy,
            "current_step": next_step_info["step"],
            "action": next_step_info["action"],
            "action_parameters": {k: v for k, v in next_step_info.items() if k not in ("step", "action")},
        })
    else:
        state.update({
            "strategy": strategy,
            "next_step": "finalize",
            "final_status": "exhausted",
            "explanation": "All strategy steps have been executed without recovery.",
            "action": "STOP_RECOVERY",
        })

    logger.info("strategy_decided", strategy=strategy, action=state.get("action"))
    return state


async def _llm_decide_strategy(state: RecoveryState) -> str | None:
    from app.agent.tools.payment_tools import decide_strategy_with_llm

    return await decide_strategy_with_llm(state)
