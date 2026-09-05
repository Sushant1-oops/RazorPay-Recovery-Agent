import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.payment_repository import PaymentRepository
from app.repositories.event_repository import EventRepository
from app.repositories.recovery_repository import RecoveryRepository
from app.models.payment_event import PaymentEvent
from app.core.logging import get_logger
from datetime import datetime, timezone

logger = get_logger("payment_service")


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.event_repo = EventRepository(session)
        self.recovery_repo = RecoveryRepository(session)

    async def process_event(self, event: PaymentEvent) -> None:
        try:
            payload = json.loads(event.payload)
            event_type = event.event_type

            logger.info("event_processing_start", event_id=event.event_id, event_type=event_type)

            payment_entity = self._extract_payment_entity(payload)
            if not payment_entity:
                await self.event_repo.mark_processed(event)
                return

            rzp_payment_id = payment_entity.get("id", "")
            payment = await self.payment_repo.get_by_razorpay_id(rzp_payment_id)

            if payment is None:
                customer_id = await self._resolve_customer_id(payment_entity)
                payment = await self.payment_repo.create(
                    razorpay_payment_id=rzp_payment_id,
                    razorpay_order_id=payment_entity.get("order_id"),
                    customer_id=customer_id,
                    amount=payment_entity.get("amount", 0),
                    currency=payment_entity.get("currency", "INR"),
                    payment_method=payment_entity.get("method"),
                    status=payment_entity.get("status", "created"),
                    failure_code=payment_entity.get("error_code"),
                    failure_reason=payment_entity.get("error_description"),
                    attempt_count=1,
                    recovered=False,
                )
            else:
                update_data = {}
                new_status = payment_entity.get("status")
                if new_status:
                    update_data["status"] = new_status

                error_code = payment_entity.get("error_code")
                if error_code:
                    update_data["failure_code"] = error_code
                    update_data["failure_reason"] = payment_entity.get("error_description")
                    update_data["attempt_count"] = payment.attempt_count + 1

                if new_status in ("captured", "authorized"):
                    update_data["recovered"] = True

                if update_data:
                    await self.payment_repo.update(payment, **update_data)

            event.payment_id = payment.id
            await self.event_repo.mark_processed(event)

            logger.info(
                "payment_updated",
                payment_id=payment.id,
                razorpay_payment_id=rzp_payment_id,
                status=payment.status,
            )

            await self._route_event(event_type, payment, payload)

        except Exception as e:
            logger.error("event_processing_failed", event_id=event.event_id, error=str(e))
            await self.event_repo.mark_failed(event)
            raise

    async def _resolve_customer_id(self, payment_entity: dict) -> int | None:
        customer_rzp_id = payment_entity.get("customer_id") or ""
        email = payment_entity.get("email")
        phone = payment_entity.get("contact")
        external_id = customer_rzp_id or (f"email:{email}" if email else None) or (f"phone:{phone}" if phone else None)
        if not external_id:
            return None
        customer = await self.payment_repo.get_or_create_customer(external_id, email=email, phone=phone)
        return customer.id

    async def _route_event(self, event_type: str, payment, payload: dict) -> None:
        if event_type == "payment.failed":
            await self._handle_payment_failed(payment, payload)
        elif event_type in ("payment.captured", "payment.authorized"):
            await self._handle_payment_success(payment, payload)
        elif event_type == "order.paid":
            await self._handle_order_paid(payment, payload)
        else:
            logger.info("event_type_not_handled", event_type=event_type)

    async def _handle_payment_failed(self, payment, payload: dict) -> None:
        from app.services.recovery_service import RecoveryService

        recovery_svc = RecoveryService(self.session)
        # 1. Check if an active or prior recovery exists for this payment
        existing = await self.recovery_repo.get_active_for_payment(payment.id)
        if not existing:
            existing = await self.recovery_repo.get_latest_for_payment(payment.id)

        # 2. Check if any prior payment under the same Razorpay order already has a recovery
        if not existing and payment.razorpay_order_id:
            prior_payments = await self.session.execute(
                select(Payment).where(
                    Payment.razorpay_order_id == payment.razorpay_order_id,
                    Payment.id != payment.id,
                )
            )
            for prior in prior_payments.scalars().all():
                existing = await self.recovery_repo.get_active_for_payment(prior.id)
                if not existing:
                    existing = await self.recovery_repo.get_latest_for_payment(prior.id)
                if existing:
                    break

        if existing is None:
            await recovery_svc.start_recovery(payment)
        else:
            await recovery_svc.resume_recovery(existing, payment, payload)

    async def _handle_payment_success(self, payment, payload: dict) -> None:
        existing = await self.recovery_repo.get_active_for_payment(payment.id)
        if not existing:
            existing = await self.recovery_repo.get_latest_for_payment(payment.id)

        # If not found directly, check prior failed payments under the same Razorpay order
        if not existing and payment.razorpay_order_id:
            prior_payments = await self.session.execute(
                select(Payment).where(
                    Payment.razorpay_order_id == payment.razorpay_order_id,
                    Payment.id != payment.id,
                )
            )
            for prior in prior_payments.scalars().all():
                existing = await self.recovery_repo.get_active_for_payment(prior.id)
                if not existing:
                    existing = await self.recovery_repo.get_latest_for_payment(prior.id)
                if existing:
                    break

        is_recovered = False
        if existing and existing.status != "recovered":
            await self.recovery_repo.update(
                existing,
                status="recovered",
                recovered_at=datetime.now(timezone.utc),
                explanation="Payment captured via recovery flow. Recovery successful.",
            )
            await self.recovery_repo.add_audit(
                recovery_id=existing.id,
                event_type="payment_recovered",
                actor="system",
                action="mark_recovered",
                metadata_={"payment_status": payment.status, "recovered_payment_id": payment.id},
            )
            is_recovered = True
        elif payment.status == "failed" or payment.recovered:
            is_recovered = True
        elif payment.razorpay_order_id:
            prior_failed = await self.session.execute(
                select(func.count()).where(
                    Payment.razorpay_order_id == payment.razorpay_order_id,
                    Payment.status == "failed",
                )
            )
            if (prior_failed.scalar() or 0) > 0:
                is_recovered = True

        await self.payment_repo.update(payment, recovered=is_recovered, status=payment.status)
        if is_recovered:
            logger.info("payment_recovered", payment_id=payment.id, razorpay_payment_id=payment.razorpay_payment_id)
        else:
            logger.info("payment_succeeded", payment_id=payment.id, razorpay_payment_id=payment.razorpay_payment_id)

    async def _handle_order_paid(self, payment, payload: dict) -> None:
        await self._handle_payment_success(payment, payload)

    def _extract_payment_entity(self, payload: dict) -> dict | None:
        p = payload.get("payload", {})
        payment_node = p.get("payment", {})
        entity = payment_node.get("entity", {})
        if entity:
            return entity
        order_node = p.get("order", {})
        order_entity = order_node.get("entity", {})
        payments = order_entity.get("payments", [])
        if payments:
            return payments[0]
        return None
