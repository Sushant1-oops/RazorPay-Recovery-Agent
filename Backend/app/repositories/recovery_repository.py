from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.recovery import Recovery
from app.models.recovery_action import RecoveryAction
from app.models.audit_log import AuditLog
from datetime import datetime, timezone


class RecoveryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, recovery_id: int) -> Recovery | None:
        return await self.session.get(Recovery, recovery_id)

    async def get_latest_for_payment(self, payment_id: int) -> Recovery | None:
        result = await self.session.execute(
            select(Recovery)
            .where(Recovery.payment_id == payment_id)
            .order_by(Recovery.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_for_payment(self, payment_id: int) -> Recovery | None:
        result = await self.session.execute(
            select(Recovery).where(
                Recovery.payment_id == payment_id,
                Recovery.status.in_(["pending", "analyzing", "executing", "observing", "adapting"])
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Recovery:
        recovery = Recovery(**kwargs)
        self.session.add(recovery)
        await self.session.flush()
        return recovery

    async def update(self, recovery: Recovery, **kwargs) -> Recovery:
        for key, value in kwargs.items():
            setattr(recovery, key, value)
        await self.session.flush()
        return recovery

    async def add_action(self, **kwargs) -> RecoveryAction:
        action = RecoveryAction(**kwargs)
        self.session.add(action)
        await self.session.flush()
        return action

    async def update_action(self, action: RecoveryAction, **kwargs) -> RecoveryAction:
        for key, value in kwargs.items():
            setattr(action, key, value)
        await self.session.flush()
        return action

    async def add_audit(self, **kwargs) -> AuditLog:
        log = AuditLog(**kwargs)
        self.session.add(log)
        await self.session.flush()
        return log

    async def list_recoveries(self, limit: int = 50, offset: int = 0) -> tuple[list[Recovery], int]:
        result = await self.session.execute(select(Recovery).order_by(Recovery.created_at.desc()))
        all_recs = result.scalars().all()
        seen = {}
        for r in all_recs:
            pid = r.payment_id
            if pid not in seen:
                seen[pid] = r
            else:
                existing = seen[pid]
                if r.status == "recovered" and existing.status != "recovered":
                    seen[pid] = r

        unique_recs = list(seen.values())
        total = len(unique_recs)
        paginated = unique_recs[offset : offset + limit]
        return paginated, total