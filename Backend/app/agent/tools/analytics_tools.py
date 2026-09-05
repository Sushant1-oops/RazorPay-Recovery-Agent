
"""Analytics tools for the recovery agent."""
from app.core.logging import get_logger

logger = get_logger("agent.analytics_tools")


def calculate_recovery_metrics(recovery_data: dict) -> dict:
    """Calculate recovery-related metrics."""
    total = recovery_data.get("total", 0)
    recovered = recovery_data.get("recovered", 0)
    rate = (recovered / total * 100) if total > 0 else 0.0

    return {
        "recovery_rate": round(rate, 2),
        "total_attempts": total,
        "successful_recoveries": recovered,
    }