"""Deterministic failure root-cause classifier.

Fallback used whenever the LLM path is disabled (SIMULATION_MODE) or fails
(see app/agent/nodes/analyze_failure.py). Rule-based on the Razorpay
failure_code / failure_reason text.
"""
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    root_cause: str
    confidence: float
    recommended_strategy: str
    reason: str
    recoverable: bool


# Known Razorpay error codes -> root cause (checked first, higher confidence).
_CODE_RULES: list[tuple[str, str]] = [
    ("bad_request_error", "invalid_payment_details"),
    ("gateway_error", "temporary_bank_error"),
    ("server_error", "temporary_bank_error"),
]

# Keyword -> root cause, checked against lowercased "failure_code failure_reason".
_KEYWORD_RULES: list[tuple[str, str]] = [
    ("insufficient", "insufficient_funds"),
    ("balance", "insufficient_funds"),
    ("timed out", "network_timeout"),
    ("timeout", "network_timeout"),
    ("network", "network_timeout"),
    ("upi", "upi_failure"),
    ("vpa", "upi_failure"),
    ("otp", "authentication_failure"),
    ("authentication", "authentication_failure"),
    ("3ds", "authentication_failure"),
    ("declined", "bank_decline"),
    ("decline", "bank_decline"),
    ("issuer", "bank_decline"),
    ("expired", "expired_payment"),
    ("card", "card_failure"),
    ("fraud", "suspected_risk"),
    ("risk", "suspected_risk"),
    ("blocked", "suspected_risk"),
    ("invalid", "invalid_payment_details"),
]

_STRATEGY_FOR_CAUSE: dict[str, str] = {
    "temporary_bank_error": "temporary_failure",
    "network_timeout": "network_timeout",
    "upi_failure": "upi_failure",
    "insufficient_funds": "notify_retry",
    "authentication_failure": "notify_retry",
    "bank_decline": "bank_decline",
    "card_failure": "notify_alternative",
    "expired_payment": "notify_retry",
    "invalid_payment_details": "notify_alternative",
    "suspected_risk": "escalate",
    "unknown": "temporary_failure",
}

_UNRECOVERABLE_CAUSES = {"invalid_payment_details", "suspected_risk"}


class FailureClassifier:
    """Rule-based fallback classifier for payment failure root cause."""

    def classify(
        self,
        failure_code: str | None,
        failure_reason: str | None,
        payment_method: str | None = None,
        amount: int = 0,
        attempt_count: int = 0,
        customer_history: dict | None = None,
    ) -> ClassificationResult:
        code = (failure_code or "").strip()
        haystack = f"{code} {failure_reason or ''}".lower()

        root_cause = None
        confidence = 0.3

        for known_code, cause in _CODE_RULES:
            if known_code in haystack:
                root_cause = cause
                confidence = 0.75
                break

        if root_cause is None:
            for keyword, cause in _KEYWORD_RULES:
                if keyword in haystack:
                    root_cause = cause
                    confidence = 0.6
                    break

        if root_cause is None:
            if payment_method == "upi":
                # UPI failures are often soft/transient even without a matching keyword.
                root_cause = "upi_failure"
                confidence = 0.4
            else:
                root_cause = "unknown"
                confidence = 0.3

        strategy = _STRATEGY_FOR_CAUSE.get(root_cause, "temporary_failure")
        recoverable = root_cause not in _UNRECOVERABLE_CAUSES

        reason = (
            f"Classified as '{root_cause}' from failure_code={code or 'n/a'!r} "
            f"and failure_reason={(failure_reason or 'n/a')!r} (confidence={confidence})."
        )

        return ClassificationResult(
            root_cause=root_cause,
            confidence=confidence,
            recommended_strategy=strategy,
            reason=reason,
            recoverable=recoverable,
        )
