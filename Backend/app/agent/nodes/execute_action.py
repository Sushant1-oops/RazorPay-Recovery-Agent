"""Execute action node — perform the validated recovery action."""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.state import RecoveryState
from app.repositories.recovery_repository import RecoveryRepository
from app.repositories.payment_repository import PaymentRepository
from app.core.logging import get_logger
from datetime import datetime, timezone

logger = get_logger("agent.execute")


async def execute_action(state: RecoveryState, session: AsyncSession) -> RecoveryState:
    """Execute the policy-validated recovery action."""
    action = state.get("action", "")
    payment_data = state.get("payment_data", {})
    recovery_repo = RecoveryRepository(session)
    payment_repo = PaymentRepository(session)

    recovery = None
    if state.get("recovery_id"):
        recovery = await recovery_repo.get_by_id(state["recovery_id"])
    if not recovery:
        recovery = await recovery_repo.get_active_for_payment(state.get("payment_id", 0))
    if not recovery:
        state["error"] = "No active recovery found"
        state["next_step"] = "finalize"
        state["final_status"] = "exhausted"
        return state

    # Create action record
    action_record = await recovery_repo.add_action(
        recovery_id=recovery.id,
        action_type=action,
        action_status="in_progress",
        reason=state.get("explanation", ""),
        parameters=json.dumps(state.get("action_parameters", {})),
        started_at=datetime.now(timezone.utc),
    )

    try:
        result = await _execute(action, state, session, recovery_repo, payment_repo)

        # Update action record
        await recovery_repo.update_action(
            action_record,
            action_status="completed",
            result=json.dumps(result),
            completed_at=datetime.now(timezone.utc),
        )

        # Update recovery
        await recovery_repo.update(
            recovery,
            status="executing",
            attempt_count=min(recovery.max_attempts, recovery.attempt_count or 1),
            current_strategy=state.get("strategy"),
            current_step=state.get("current_step"),
            next_action=action,
            explanation=state.get("explanation"),
        )

        # Add audit log
        await recovery_repo.add_audit(
            recovery_id=recovery.id,
            event_type="action_completed",
            actor="agent",
            action=action,
            metadata_={"result": result},
        )

        state["action_result"] = result
        logger.info("action_executed", action=action, result=result)

    except Exception as e:
        await recovery_repo.update_action(
            action_record,
            action_status="failed",
            result=json.dumps({"error": str(e)}),
            completed_at=datetime.now(timezone.utc),
        )
        await recovery_repo.add_audit(
            recovery_id=recovery.id,
            event_type="action_failed",
            actor="agent",
            action=action,
            metadata_={"error": str(e)},
        )
        state["action_result"] = {"error": str(e)}
        logger.error("action_execution_failed", action=action, error=str(e))

    return state


async def _execute(
    action: str,
    state: RecoveryState,
    session: AsyncSession,
    recovery_repo: RecoveryRepository,
    payment_repo: PaymentRepository,
) -> dict:
    """Execute a specific action."""
    payment_data = state.get("payment_data", {})
    recovery = None
    if state.get("recovery_id"):
        recovery = await recovery_repo.get_by_id(state["recovery_id"])
    if not recovery:
        recovery = await recovery_repo.get_active_for_payment(state.get("payment_id", 0))

    if action == "CHECK_PAYMENT_STATUS":
        from app.services.razorpay_service import RazorpayService

        rzp = RazorpayService()
        live = rzp.check_payment_status_safely(payment_data.get("razorpay_payment_id", ""))
        if live.get("status") in ("unknown", None) and not live.get("error"):
            live["status"] = payment_data.get("status", "failed")
            live["safe_to_retry"] = live["status"] in ("failed", "created")
        return live

    elif action == "RETRY_PAYMENT_FLOW":
        from app.services.razorpay_service import RazorpayService
        from app.core.exceptions import RazorpayAPIError

        rzp = RazorpayService()
        if not rzp.configured:
            return {
                "status": "retry_prepared",
                "note": "Razorpay keys not set; logged retry intent without creating a new order.",
            }
        try:
            order = rzp.create_order(
                amount=payment_data.get("amount", 0),
                currency=payment_data.get("currency", "INR"),
                receipt=f"recovery_{recovery.id if recovery else 'na'}",
            )
            return {"status": "retry_initiated", "order_id": order.get("id")}
        except RazorpayAPIError as e:
            return {"status": "retry_failed", "error": str(e)}

    elif action == "SEND_NOTIFICATION":
        from app.services.notification_service import NotificationService
        from app.services.razorpay_service import RazorpayService
        notif_svc = NotificationService(session)
        customer_data = state.get("customer_data", {})
        message = _generate_customer_message(state)
        channel = "email"
        recipient = customer_data.get("email") or payment_data.get("email", "")
        if not recipient:
            channel = "mock"
            recipient = "customer@example.com"

        rzp_svc = RazorpayService()
        payment_url = None
        amount = payment_data.get("amount", 0)
        if rzp_svc.configured and amount > 0:
            link_res = rzp_svc.create_payment_link(
                amount=amount,
                description=f"Recovery for order {payment_data.get('razorpay_order_id') or payment_data.get('razorpay_payment_id', '')}",
                customer_email=recipient,
            )
            payment_url = link_res.get("short_url")

        notif = await notif_svc.send_notification(
            recovery_id=recovery.id if recovery else None,
            channel=channel,
            recipient=recipient,
            message=message,
            template=state.get("action_parameters", {}).get("template"),
            payment_url=payment_url,
        )
        return {"status": "sent", "notification_id": notif.id, "channel": channel, "payment_url": payment_url}

    elif action == "OFFER_ALTERNATIVE_PAYMENT":
        from app.services.notification_service import NotificationService
        from app.services.razorpay_service import RazorpayService
        notif_svc = NotificationService(session)
        message = (
            "Your payment could not be completed. "
            "Please try again using another payment method such as a different card, UPI app, or netbanking."
        )
        customer_data = state.get("customer_data", {})
        recipient = customer_data.get("email") or "customer@example.com"

        rzp_svc = RazorpayService()
        payment_url = None
        amount = payment_data.get("amount", 0)
        if rzp_svc.configured and amount > 0:
            link_res = rzp_svc.create_payment_link(
                amount=amount,
                description=f"Retry with alternative method for {payment_data.get('razorpay_order_id') or payment_data.get('razorpay_payment_id', '')}",
                customer_email=recipient,
            )
            payment_url = link_res.get("short_url")

        notif = await notif_svc.send_notification(
            recovery_id=recovery.id if recovery else None,
            channel="email",
            recipient=recipient,
            message=message,
            template="alternative_method",
            payment_url=payment_url,
        )
        return {"status": "alternative_offered", "notification_id": notif.id, "payment_url": payment_url}

    elif action == "ESCALATE_TO_SUPPORT":
        from app.services.notification_service import NotificationService
        notif_svc = NotificationService(session)
        message = f"Payment recovery requires manual intervention. Payment: {payment_data.get('razorpay_payment_id')}, Amount: {payment_data.get('amount')}"
        await notif_svc.send_notification(
            recovery_id=recovery.id if recovery else None,
            channel="email",
            recipient="support@merchant.com",
            message=message,
            template="escalation",
        )
        return {"status": "escalated"}

    elif action == "STOP_RECOVERY":
        return {"status": "stopped"}

    elif action == "WAIT_FOR_EVENT":
        return {"status": "waiting_for_event"}

    else:
        return {"status": "unknown_action", "action": action}


def _generate_customer_message(state: RecoveryState) -> str:
    """Generate a customer-facing message."""
    root_cause = state.get("root_cause", "")
    payment_data = state.get("payment_data", {})
    amount = payment_data.get("amount", 0)
    amount_display = f"INR {amount // 100}" if amount >= 100 else f"INR {amount}"

    messages = {
        "temporary_bank_error": f"Your payment of {amount_display} could not be processed due to a temporary bank issue. Please try again in a few minutes.",
        "network_timeout": f"Your payment of {amount_display} timed out. Please retry the payment.",
        "upi_failure": f"Your UPI payment of {amount_display} failed. Please try again or use a different payment method.",
        "bank_decline": f"Your bank declined the payment of {amount_display}. Please contact your bank or try another payment method.",
        "insufficient_funds": f"Your payment of {amount_display} could not be processed. Please ensure sufficient funds are available and try again.",
        "authentication_failure": f"Payment authentication failed for {amount_display}. Please retry and complete the authentication step.",
        "suspected_risk": f"Your payment of {amount_display} was blocked for security reasons. Please contact support for assistance.",
    }

    return messages.get(root_cause, f"Your payment of {amount_display} could not be completed. Please try again.")