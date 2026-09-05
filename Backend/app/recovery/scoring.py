"""Deterministic recovery scoring engine.

Returns a score from 0-100 representing the probability of recovery.
"""
from app.core.logging import get_logger

logger = get_logger("scoring")


class RecoveryScorer:
    """Calculate deterministic recoverability score."""

    def score(
        self,
        root_cause: str,
        root_cause_confidence: float,
        attempt_count: int,
        payment_method: str | None = None,
        amount: int = 0,
        customer_history: dict | None = None,
    ) -> float:
        """Calculate recoverability score (0-100)."""
        customer_history = customer_history or {}
        score = 50.0  # Base score

        # Factor 1: Root cause
        cause_scores = {
            "temporary_bank_error": 35,
            "network_timeout": 30,
            "upi_failure": 25,
            "insufficient_funds": 15,
            "authentication_failure": 10,
            "bank_decline": 5,
            "card_failure": 10,
            "expired_payment": 20,
            "invalid_payment_details": 10,
            "suspected_risk": -30,
            "unknown": 0,
        }
        score += cause_scores.get(root_cause, 0)

        # Factor 2: Root cause confidence
        score += root_cause_confidence * 10

        # Factor 3: Attempt count (diminishing returns)
        attempt_penalty = min(attempt_count * 15, 45)
        score -= attempt_penalty

        # Factor 4: Customer history
        if customer_history.get("has_previous_success"):
            score += 10
        if customer_history.get("success_rate", 0) > 0.8:
            score += 5
        if not customer_history.get("is_returning_customer"):
            score -= 5

        # Factor 5: Payment method
        method_bonus = {"upi": 3, "card": 0, "netbanking": -2, "wallet": -5}
        score += method_bonus.get(payment_method or "", 0)

        # Factor 6: Amount (higher amounts slightly harder to recover)
        if amount > 500000:  # > 5000 INR
            score -= 5
        if amount > 2000000:  # > 20000 INR
            score -= 5

        # Clamp
        score = max(0.0, min(100.0, score))

        return round(score, 2)

    def categorize(self, score: float) -> str:
        """Categorize recovery score."""
        if score >= 85:
            return "highly_recoverable"
        elif score >= 60:
            return "recoverable"
        elif score >= 30:
            return "uncertain"
        else:
            return "low_recoverability"