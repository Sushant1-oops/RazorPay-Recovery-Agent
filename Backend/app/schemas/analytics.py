from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    total_payments: int
    successful_payments: int
    failed_payments: int
    recoverable_payments: int
    recovered_payments: int
    recovery_rate: float
    total_recovered_revenue: int
    average_recovery_time_seconds: float | None = None


class RecoveryRateResponse(BaseModel):
    recovery_rate: float
    recoverable: int
    recovered: int
    exhausted: int
    escalated: int


class RecoveredRevenueResponse(BaseModel):
    total_recovered_amount: int
    currency: str
    recovery_count: int


class FailureBreakdownItem(BaseModel):
    failure_type: str
    count: int
    percentage: float


class FailureBreakdownResponse(BaseModel):
    breakdown: list[FailureBreakdownItem]


class StrategyItem(BaseModel):
    strategy: str
    count: int
    success_rate: float


class RecoveryStrategiesResponse(BaseModel):
    strategies: list[StrategyItem]