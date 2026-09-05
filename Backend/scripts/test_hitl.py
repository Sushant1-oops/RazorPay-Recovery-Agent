"""Verification script for Human-in-the-Loop escalation workflow."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.database import async_session
from app.models.payment import Payment
from app.models.recovery import Recovery
from app.services.recovery_service import RecoveryService
from app.agent.graph import RecoveryAgent
from app.recovery.state_machine import can_transition, is_terminal


async def run_tests():
    print("=== Testing Human-in-the-Loop (HITL) Workflow ===")

    # 1. Test State Machine Transitions
    print("\n--- 1. Testing State Machine ---")
    assert can_transition("analyzing", "escalated") is True, "analyzing -> escalated should be allowed"
    assert can_transition("executing", "escalated") is True, "executing -> escalated should be allowed"
    assert can_transition("observing", "escalated") is True, "observing -> escalated should be allowed"
    assert can_transition("escalated", "pending") is True, "escalated -> pending (approve retry) should be allowed"
    assert can_transition("escalated", "exhausted") is True, "escalated -> exhausted (reject) should be allowed"
    assert can_transition("escalated", "recovered") is True, "escalated -> recovered (resolve) should be allowed"
    assert is_terminal("escalated") is False, "escalated should NOT be terminal (it awaits human review)"
    print("[OK] State machine transitions verified!")

    async with async_session() as session:
        svc = RecoveryService(session)

        # 2. Test Low Recoverability & High Ambiguity Escalation
        print("\n--- 2. Testing Ambiguity / Low Recoverability Escalation ---")
        # Create a mock failed payment with ambiguous root cause
        payment = Payment(
            razorpay_payment_id=f"pay_test_{int(datetime.now().timestamp())}",
            razorpay_order_id=f"order_test_{int(datetime.now().timestamp())}",
            amount=5000000,  # ₹50,000 (high value)
            currency="INR",
            status="failed",
            failure_code="BAD_REQUEST_ERROR",
            failure_reason="Payment failed due to ambiguous bank error",
            payment_method="card",
            attempt_count=1,
            recovered=False,
        )
        session.add(payment)
        await session.flush()

        recovery = Recovery(
            payment_id=payment.id,
            status="pending",
            attempt_count=1,
            max_attempts=3,
        )
        session.add(recovery)
        await session.commit()

        # Run agent
        agent = RecoveryAgent(session)
        result = await agent.run(recovery.id)
        
        # Reload recovery
        recovery = await session.get(Recovery, recovery.id)
        print(f"Result Status: {recovery.status}")
        print(f"Explanation: {recovery.explanation}")
        print(f"Strategy: {recovery.current_strategy}")
        assert recovery.status == "escalated", f"Expected 'escalated', got '{recovery.status}'"
        print("[OK] Agent properly escalated ambiguous/high-amount case to 'escalated'!")

        # 3. Test Human Review: Approve Retry
        print("\n--- 3. Testing Human Review: Approve Retry ---")
        review_result = await svc.review_recovery(
            recovery_id=recovery.id,
            decision="approve_retry",
            notes="Operator verified customer identity and approved retry.",
            reviewer="support_lead@merchant.com",
        )
        await session.commit()
        recovery = await session.get(Recovery, recovery.id)
        print(f"Review Result: {review_result}")
        print(f"New Recovery Status: {recovery.status}")
        # When approved with operator_override, agent executes the recovery steps
        assert recovery.status in ("observing", "recovered", "executing"), f"Status should progress, got {recovery.status}"
        print("[OK] Human operator approved retry successfully!")

        # 4. Test Human Review: Reject
        print("\n--- 4. Testing Human Review: Reject ---")
        # Set back to escalated
        recovery.status = "escalated"
        await session.commit()

        reject_result = await svc.review_recovery(
            recovery_id=recovery.id,
            decision="reject",
            notes="Customer indicated they do not wish to proceed.",
            reviewer="support_lead@merchant.com",
        )
        await session.commit()
        recovery = await session.get(Recovery, recovery.id)
        assert recovery.status == "exhausted", f"Expected 'exhausted', got '{recovery.status}'"
        print("[OK] Human operator rejected recovery successfully!")

        # 5. Test Human Review: Resolve
        print("\n--- 5. Testing Human Review: Mark Resolved ---")
        recovery.status = "escalated"
        await session.commit()

        resolve_result = await svc.review_recovery(
            recovery_id=recovery.id,
            decision="resolve",
            notes="Customer paid via offline NEFT transfer.",
            reviewer="support_lead@merchant.com",
        )
        await session.commit()
        recovery = await session.get(Recovery, recovery.id)
        payment = await session.get(Payment, recovery.payment_id)
        assert recovery.status == "recovered", f"Expected 'recovered', got '{recovery.status}'"
        assert payment.recovered is True, "Payment recovered flag should be True"
        assert payment.status == "captured", "Payment status should be captured"
        print("[OK] Human operator marked manual resolution successfully!")

        # Clean up test rows
        from sqlalchemy import delete
        from app.models.recovery_action import RecoveryAction
        from app.models.audit_log import AuditLog
        from app.models.notification import Notification
        await session.execute(delete(RecoveryAction).where(RecoveryAction.recovery_id == recovery.id))
        await session.execute(delete(AuditLog).where(AuditLog.recovery_id == recovery.id))
        await session.execute(delete(Notification).where(Notification.recovery_id == recovery.id))
        await session.delete(recovery)
        await session.delete(payment)
        await session.commit()
        print("[OK] Test cleanup completed!")

    print("\n=== ALL HITL TESTS PASSED! ===")


if __name__ == "__main__":
    asyncio.run(run_tests())
