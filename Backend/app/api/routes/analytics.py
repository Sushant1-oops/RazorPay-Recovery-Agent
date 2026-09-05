from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    AnalyticsOverview,
    RecoveryRateResponse,
    RecoveredRevenueResponse,
    FailureBreakdownResponse,
    RecoveryStrategiesResponse,
)
from app.models.user import User

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def analytics_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = AnalyticsService(db)
    data = await svc.get_overview()
    return AnalyticsOverview(**data)


@router.get("/recovery-rate", response_model=RecoveryRateResponse)
async def recovery_rate(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = AnalyticsService(db)
    data = await svc.get_recovery_rate()
    return RecoveryRateResponse(**data)


@router.get("/recovered-revenue", response_model=RecoveredRevenueResponse)
async def recovered_revenue(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = AnalyticsService(db)
    data = await svc.get_recovered_revenue()
    return RecoveredRevenueResponse(**data)


@router.get("/failure-breakdown", response_model=FailureBreakdownResponse)
async def failure_breakdown(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = AnalyticsService(db)
    data = await svc.get_failure_breakdown()
    return FailureBreakdownResponse(**data)


@router.get("/recovery-strategies", response_model=RecoveryStrategiesResponse)
async def recovery_strategies(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = AnalyticsService(db)
    data = await svc.get_recovery_strategies()
    return RecoveryStrategiesResponse(**data)