"""Tools for the recovery agent — LLM interactions and payment operations."""
from app.agent.state import RecoveryState
from app.core.config import settings
from app.core.logging import get_logger
from pydantic import BaseModel

logger = get_logger("agent.tools")


class LLMSchema(BaseModel):
    """Schema for structured LLM output."""
    pass


async def get_llm():
    """Get the configured Groq LLM."""
    from langchain_groq import ChatGroq
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        timeout=20,
        max_retries=1,
    )


class FailureAnalysisResult(BaseModel):
    root_cause: str
    confidence: float
    recoverable: bool
    reason: str
    recommended_strategy: str


async def analyze_failure_with_llm(state: RecoveryState) -> FailureAnalysisResult | None:
    """Use LLM for failure analysis. Returns structured result."""
    try:
        llm = await get_llm()
        structured_llm = llm.with_structured_output(FailureAnalysisResult)

        prompt = f"""You are a payment failure analysis system.
Analyze the supplied payment event, failure code, payment method,
customer history, and previous recovery attempts.

Determine the most likely root cause.
Return only the required structured schema.
Confidence must be a float between 0.0 and 1.0 (e.g. 0.85 for 85% certainty).

Never invent payment information.
Never directly authorize a financial transaction.

Payment data: {state.get('payment_data', {})}
Failure code: {state.get('failure_code', '')}
Failure reason: {state.get('failure_reason', '')}
Customer history: {state.get('customer_data', {})}
Previous actions: {state.get('previous_actions', [])}

Valid root causes: insufficient_funds, bank_decline, temporary_bank_error, network_timeout, upi_failure, card_failure, authentication_failure, expired_payment, invalid_payment_details, suspected_risk, unknown

Valid strategies: temporary_failure, upi_failure, bank_decline, network_timeout, notify_retry, notify_alternative, escalate, low_recoverability"""

        result = await structured_llm.ainvoke(prompt)
        return result
    except Exception as e:
        logger.warning("llm_failure_analysis_failed", error=str(e))
        return None


class StrategyRecommendation(BaseModel):
    strategy: str
    reason: str


async def decide_strategy_with_llm(state: RecoveryState) -> str | None:
    """Use LLM to recommend a recovery strategy."""
    try:
        llm = await get_llm()
        structured_llm = llm.with_structured_output(StrategyRecommendation)

        prompt = f"""You are the decision layer of an autonomous payment recovery system.

Given the payment state, failure diagnosis, customer history,
previous recovery actions, and policy constraints, recommend
the safest recovery strategy.

You must prefer:
1. Avoiding duplicate charges.
2. Checking ambiguous payment status.
3. Limited retries.
4. Alternative payment flows when appropriate.
5. Escalation when automation is unsafe.

Return structured output only.

Root cause: {state.get('root_cause', '')}
Confidence: {state.get('root_cause_confidence', 0)}
Recoverability score: {state.get('recoverability_score', 0)}
Payment data: {state.get('payment_data', {})}
Previous actions: {state.get('previous_actions', [])}

Valid strategies: temporary_failure, upi_failure, bank_decline, network_timeout, notify_retry, notify_alternative, escalate, low_recoverability"""

        result = await structured_llm.ainvoke(prompt)
        return result.strategy
    except Exception as e:
        logger.warning("llm_strategy_decision_failed", error=str(e))
        return None