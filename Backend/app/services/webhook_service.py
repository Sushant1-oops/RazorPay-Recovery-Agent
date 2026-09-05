import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.event_repository import EventRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.razorpay_service import RazorpayService
from app.core.exceptions import WebhookSignatureError, DuplicateEventError
from app.core.logging import get_logger

logger = get_logger("webhook")


class WebhookService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.event_repo = EventRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.razorpay = RazorpayService()

    async def ingest_webhook(self, raw_body: str, signature: str) -> dict:
        if not self.razorpay.verify_webhook_signature(raw_body, signature):
            logger.warning("webhook_signature_invalid")
            raise WebhookSignatureError()

        event_data = json.loads(raw_body)
        event_id = event_data.get("id") or f"evt_{uuid.uuid4().hex[:20]}"
        event_type = event_data.get("event", "")

        logger.info("webhook_received", event_id=event_id, event_type=event_type)

        if await self.event_repo.exists(event_id):
            logger.info("webhook_duplicate", event_id=event_id)
            raise DuplicateEventError(detail="Event already processed")

        payment_entity = self._extract_payment_entity(event_data)
        rzp_payment_id = payment_entity.get("id", "") if payment_entity else ""

        event = await self.event_repo.create(
            event_id=event_id,
            event_type=event_type,
            razorpay_payment_id=rzp_payment_id,
            payload=raw_body,
            signature=signature,
            processing_status="pending",
        )
        await self.session.commit()

        from app.services.payment_service import PaymentService

        payment_svc = PaymentService(self.session)
        await payment_svc.process_event(event)
        await self.session.commit()

        logger.info("webhook_processed", event_id=event_id, event_type=event_type)

        return {
            "event_id": event_id,
            "event_type": event_type,
            "status": "processed",
            "message": "Event processed",
        }

    def _extract_payment_entity(self, event_data: dict) -> dict | None:
        payload = event_data.get("payload", {})
        payment_node = payload.get("payment", {})
        entity = payment_node.get("entity", {})
        if entity:
            return entity
        order_node = payload.get("order", {})
        order_entity = order_node.get("entity", {})
        payments = order_entity.get("payments", [])
        if payments:
            return payments[0]
        return None
