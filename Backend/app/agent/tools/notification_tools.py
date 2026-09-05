"""Notification tools for the recovery agent."""
from app.core.logging import get_logger

logger = get_logger("agent.notification_tools")


def generate_customer_message(root_cause: str, amount: int, currency: str = "INR") -> str:
    """Generate a customer notification message based on root cause."""
    amount_display = f"INR {amount // 100}" if amount >= 100 else f"{amount} {currency}"

    templates = {
        "temporary_bank_error": f"Your payment of {amount_display} could not be processed due to a temporary issue. Please try again shortly.",
        "network_timeout": f"Your payment of {amount_display} timed out. Please retry.",
        "upi_failure": f"Your UPI payment of {amount_display} failed. Please try again or use a different payment method.",
        "bank_decline": f"Your bank declined the payment of {amount_display}. Please try another payment method.",
        "insufficient_funds": f"Payment of {amount_display} failed. Please ensure sufficient balance and retry.",
        "authentication_failure": f"Payment authentication failed for {amount_display}. Please retry and complete verification.",
    }

    return templates.get(
        root_cause,
        f"Your payment of {amount_display} could not be completed. Please try again or contact support.",
    )