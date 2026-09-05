"""Policy engine — the safety layer.

The AI agent proposes an action. The policy engine decides whether
that action is allowed. This is a critical financial safety component.
"""
from app.core.config import settings
from app.core.exceptions import PolicyViolationError
from app.core.logging import get_logger
from pydantic import BaseModel
from datetime import datetime, timezone

logger = get_logger("policy")


class PolicyResult(BaseModel):
    allowed: bool
    action: str
    reason: str
    constraints: dict = {}


class RecoveryPolicy:
    """Enforce safety policies on all recovery actions."""

    def validate(
        self,
        action: str,
        payment_status: str,
        attempt_count: int,
        max_attempts: int,
        recovery_status: str,
        parameters: dict | None = None,
    ) -> PolicyResult:
        """Validate whether an action is allowed by policy."""
        parameters = parameters or {}

        # Rule 1: If payment already captured, block all payment actions
        if payment_status in ("captured", "authorized") and action in (
            "RETRY_PAYMENT_FLOW", "CHECK_PAYMENT_STATUS", "OFFER_ALTERNATIVE_PAYMENT",
        ):
            result = PolicyResult(
                allowed=False,
                action=action,
                reason=f"Payment is already {payment_status}. No payment actions allowed.",
                constraints={"payment_status": payment_status},
            )
            logger.warning("policy_violation", action=action, reason=result.reason)
            return result

        # Rule 2: Max retry limit
        if action == "RETRY_PAYMENT_FLOW" and attempt_count >= max_attempts:
            result = PolicyResult(
                allowed=False,
                action=action,
                reason=f"Maximum retry attempts ({max_attempts}) reached.",
                constraints={"attempt_count": attempt_count, "max_attempts": max_attempts},
            )
            logger.warning("policy_violation", action=action, reason=result.reason)
            return result

        # Rule 3: Must check status before retry if payment state is ambiguous
        if action == "RETRY_PAYMENT_FLOW" and payment_status in ("pending", "unknown"):
            result = PolicyResult(
                allowed=False,
                action=action,
                reason="Payment status is ambiguous. Must check status before retry.",
                constraints={"required_pre_action": "CHECK_PAYMENT_STATUS"},
            )
            logger.warning("policy_violation", action=action, reason=result.reason)
            return result

        # Rule 4: Block actions on terminal recovery states
        if recovery_status in ("recovered", "exhausted", "escalated", "unsafe_to_retry", "cancelled"):
            result = PolicyResult(
                allowed=False,
                action=action,
                reason=f"Recovery is in terminal state: {recovery_status}.",
                constraints={"recovery_status": recovery_status},
            )
            logger.warning("policy_violation", action=action, reason=result.reason)
            return result

        # Rule 5: Minimum retry interval
        if action == "RETRY_PAYMENT_FLOW":
            # This would check timing in production
            pass

        # Rule 6: Never allow duplicate charges
        if action == "RETRY_PAYMENT_FLOW" and parameters.get("force_create", False):
            result = PolicyResult(
                allowed=False,
                action=action,
                reason="Force-creating a new charge is not allowed. Must verify existing payment status first.",
                constraints={"force_create_blocked": True},
            )
            logger.warning("policy_violation", action=action, reason=result.reason)
            return result

        # Rule 7: Notifications have their own limits
        if action == "SEND_NOTIFICATION" and parameters.get("notification_count", 0) >= 3:
            result = PolicyResult(
                allowed=False,
                action=action,
                reason="Maximum notification count reached for this recovery.",
                constraints={"notification_count": parameters["notification_count"]},
            )
            return result

        # All checks passed
        allowed_actions = [
            "CHECK_PAYMENT_STATUS",
            "RETRY_PAYMENT_FLOW",
            "SEND_NOTIFICATION",
            "OFFER_ALTERNATIVE_PAYMENT",
            "ESCALATE_TO_SUPPORT",
            "STOP_RECOVERY",
            "WAIT_FOR_EVENT",
        ]

        if action not in allowed_actions:
            result = PolicyResult(
                allowed=False,
                action=action,
                reason=f"Unknown action: {action}.",
            )
            logger.warning("policy_violation", action=action, reason=result.reason)
            return result

        logger.info("policy_check_passed", action=action)
        return PolicyResult(
            allowed=True,
            action=action,
            reason="Action allowed by policy.",
            constraints={},
        )