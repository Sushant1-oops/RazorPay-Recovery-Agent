from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.payment_event import PaymentEvent
from datetime import datetime, timezone


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def exists(self, event_id: str) -> bool:
        result = await self.session.execute(select(PaymentEvent.id).where(PaymentEvent.event_id == event_id).limit(1))
        return result.scalar_one_or_none() is not None

    async def create(self, **kwargs) -> PaymentEvent:
        event = PaymentEvent(**kwargs)
        self.session.add(event)
        await self.session.flush()
        return event

    async def mark_processed(self, event: PaymentEvent) -> PaymentEvent:
        event.processed_at = datetime.now(timezone.utc)
        event.processing_status = "processed"
        await self.session.flush()
        return event

    async def mark_failed(self, event: PaymentEvent) -> PaymentEvent:
        event.processing_status = "failed"
        await self.session.flush()
        return event