"""Ingest event node — load payment and event data into state."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agent.state import RecoveryState
from app.repositories.payment_repository import PaymentRepository
from app.repositories.recovery_repository import RecoveryRepository
from app.models.payment_event import PaymentEvent
from app.core.logging import get_logger

logger = get_logger("agent.ingest")


async def ingest_event(state: RecoveryState, session: AsyncSession) -> RecoveryState:
    payment_repo = PaymentRepository(session)
    recovery_repo = RecoveryRepository(session)

    payment_id = state.get("payment_id", 0)
    payment = await payment_repo.get_by_id(payment_id)

    if not payment:
        state["error"] = f"Payment {payment_id} not found"
        state["next_step"] = "finalize"
        state["final_status"] = "exhausted"
        return state

    customer_data = {}
    if payment.customer_id:
        from app.services.customer_service import CustomerService

        customer_svc = CustomerService(session)
        customer_data = await customer_svc.get_customer_history(payment.customer_id)

    result = await session.execute(
        select(PaymentEvent)
        .where(PaymentEvent.razorpay_payment_id == payment.razorpay_payment_id)
        .order_by(PaymentEvent.received_at.desc())
        .limit(5)
    )
    recent_events = [
        {"event_id": e.event_id, "event_type": e.event_type, "received_at": str(e.received_at)}
        for e in result.scalars().all()
    ]

    recovery = None
    if state.get("recovery_id"):
        recovery = await recovery_repo.get_by_id(state["recovery_id"])
    if recovery is None:
        recovery = await recovery_repo.get_active_for_payment(payment_id)

    previous_actions = []
    if recovery:
        from app.models.recovery_action import RecoveryAction
        action_res = await session.execute(
            select(RecoveryAction).where(RecoveryAction.recovery_id == recovery.id)
        )
        previous_actions = [
            {
                "action_type": a.action_type,
                "action_status": a.action_status,
                "reason": a.reason,
                "result": a.result,
            }
            for a in action_res.scalars().all()
        ]

    state.update({
        "recovery_id": recovery.id if recovery else state.get("recovery_id"),
        "payment_data": {
            "id": payment.id,
            "razorpay_payment_id": payment.razorpay_payment_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "payment_method": payment.payment_method,
            "failure_code": payment.failure_code,
            "failure_reason": payment.failure_reason,
            "attempt_count": payment.attempt_count,
            "email": customer_data.get("email"),
        },
        "customer_data": customer_data,
        "recent_events": recent_events,
        "failure_reason": payment.failure_reason or "",
        "failure_code": payment.failure_code or "",
        "previous_actions": previous_actions,
        "strategy": state.get("strategy") or (recovery.current_strategy if recovery else None) or "",
        "current_step": state.get("current_step") or (recovery.current_step if recovery else None) or "",
    })

    logger.info("event_ingested", payment_id=payment_id, status=payment.status)
    return state
