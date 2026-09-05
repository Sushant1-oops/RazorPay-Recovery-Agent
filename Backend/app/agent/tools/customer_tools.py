"""Customer tools for the recovery agent."""
from app.core.logging import get_logger

logger = get_logger("agent.customer_tools")


async def get_customer_summary(customer_data: dict) -> str:
    """Generate a customer summary for LLM context."""
    if not customer_data:
        return "No customer history available."

    parts = [
        f"Total payments: {customer_data.get('total_payments', 0)}",
        f"Successful: {customer_data.get('successful_payments', 0)}",
        f"Failed: {customer_data.get('failed_payments', 0)}",
        f"Success rate: {customer_data.get('success_rate', 0):.2%}",
        f"Returning customer: {'Yes' if customer_data.get('is_returning_customer') else 'No'}",
    ]
    return "\n".join(parts)