from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from app.models.payment import Payment
from app.models.recovery import Recovery
from app.core.logging import get_logger
from datetime import datetime, timezone

logger = get_logger("analytics_service")


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_overview(self) -> dict:
        """Get analytics overview."""
        # Total payments
        total = (await self.session.execute(select(func.count()).select_from(Payment))).scalar() or 0

        # Successful (captured or authorized)
        successful = (
            await self.session.execute(
                select(func.count()).where(Payment.status.in_(["captured", "authorized"]))
            )
        ).scalar() or 0

        # Failed
        failed = (await self.session.execute(select(func.count()).where(Payment.status == "failed"))).scalar() or 0

        # Recoverable (currently active in recovery pipeline)
        recoverable = (
            await self.session.execute(
                select(func.count(func.distinct(Recovery.payment_id)))
                .where(Recovery.status.in_(["pending", "analyzing", "executing", "observing", "adapting"]))
            )
        ).scalar() or 0

        # Recovered
        recovered = (
            await self.session.execute(
                select(func.count(func.distinct(Payment.id)))
                .where(Payment.recovered == True, Payment.status.in_(["captured", "authorized", "recovered"]))
            )
        ).scalar() or 0

        # Total recovered revenue
        recovered_revenue = (
            await self.session.execute(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(
                    Payment.recovered == True,
                    Payment.status.in_(["captured", "authorized", "recovered"]),
                )
            )
        ).scalar() or 0

        # Average recovery time
        avg_time = (
            await self.session.execute(
                select(
                    func.coalesce(
                        func.avg(
                            func.extract("epoch", Recovery.recovered_at - Recovery.created_at)
                        ),
                        0,
                    )
                ).where(Recovery.status == "recovered", Recovery.recovered_at.isnot(None))
            )
        ).scalar() or 0

        total_failed_pool = failed + recovered
        recovery_rate = (recovered / total_failed_pool * 100) if total_failed_pool > 0 else 0.0

        return {
            "total_payments": total,
            "successful_payments": successful,
            "failed_payments": failed,
            "recoverable_payments": recoverable,
            "recovered_payments": recovered,
            "recovery_rate": round(recovery_rate, 2),
            "total_recovered_revenue": int(recovered_revenue),
            "average_recovery_time_seconds": round(float(avg_time), 2),
        }

    async def get_recovery_rate(self) -> dict:
        recovered = (
            await self.session.execute(select(func.count()).where(Recovery.status == "recovered"))
        ).scalar() or 0
        exhausted = (
            await self.session.execute(select(func.count()).where(Recovery.status == "exhausted"))
        ).scalar() or 0
        escalated = (
            await self.session.execute(select(func.count()).where(Recovery.status == "escalated"))
        ).scalar() or 0
        total_recoverable = recovered + exhausted + escalated
        rate = (recovered / total_recoverable * 100) if total_recoverable > 0 else 0.0

        return {
            "recovery_rate": round(rate, 2),
            "recoverable": total_recoverable,
            "recovered": recovered,
            "exhausted": exhausted,
            "escalated": escalated,
        }

    async def get_recovered_revenue(self) -> dict:
        result = (
            await self.session.execute(
                select(func.coalesce(func.sum(Payment.amount), 0), func.count())
                .select_from(Payment)
                .where(Payment.recovered == True, Payment.status.in_(["captured", "authorized", "recovered"]))
            )
        ).one()
        return {
            "total_recovered_amount": int(result[0]),
            "currency": "INR",
            "recovery_count": result[1],
        }

    async def get_failure_breakdown(self) -> dict:
        result = await self.session.execute(
            select(
                Payment.id,
                Payment.failure_code,
                Recovery.root_cause,
            )
            .select_from(Payment)
            .outerjoin(Recovery, Payment.id == Recovery.payment_id)
            .where(Payment.status == "failed")
        )
        counts: dict[str, set[int]] = {}
        for payment_id, failure_code, root_cause in result.all():
            cause = (root_cause or failure_code or "unknown").replace("_", " ")
            if cause not in counts:
                counts[cause] = set()
            counts[cause].add(payment_id)

        total = sum(len(ids) for ids in counts.values()) or 1
        breakdown = [
            {
                "failure_type": cause,
                "count": len(ids),
                "percentage": round(len(ids) / total * 100, 2),
            }
            for cause, ids in sorted(counts.items(), key=lambda x: len(x[1]), reverse=True)
        ]
        return {"breakdown": breakdown}

    async def get_recovery_strategies(self) -> dict:
        result = await self.session.execute(
            select(Recovery.current_strategy, func.count(func.distinct(Recovery.payment_id)).label("cnt"))
            .where(Recovery.current_strategy.isnot(None))
            .group_by(Recovery.current_strategy)
        )
        strategies = []
        for row in result.all():
            strategy = row[0]
            count = row[1]
            success = (
                await self.session.execute(
                    select(func.count(func.distinct(Recovery.payment_id)))
                    .where(Recovery.current_strategy == strategy, Recovery.status == "recovered")
                )
            ).scalar() or 0
            strategies.append({
                "strategy": strategy.replace("_", " "),
                "count": count,
                "success_rate": round(success / count * 100, 2) if count > 0 else 0.0,
            })
        return {"strategies": strategies}