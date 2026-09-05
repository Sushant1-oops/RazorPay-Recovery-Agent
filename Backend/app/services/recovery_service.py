"""Creates recoveries and runs the LangGraph agent inline."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.recovery_repository import RecoveryRepository
from app.repositories.payment_repository import PaymentRepository
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("recovery_service")


class RecoveryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.recovery_repo = RecoveryRepository(session)
        self.payment_repo = PaymentRepository(session)

    async def start_recovery(self, payment):
        recovery = await self.recovery_repo.create(
            payment_id=payment.id,
            status="pending",
            attempt_count=1,
            max_attempts=settings.MAX_RECOVERY_ATTEMPTS,
        )
        await self.recovery_repo.add_audit(
            recovery_id=recovery.id,
            event_type="recovery_started",
            actor="system",
            action="start_recovery",
            metadata_={"payment_id": payment.id},
        )
        await self.session.commit()
        await self._run_agent(recovery.id)
        return recovery

    async def resume_recovery(self, recovery, payment, payload: dict):
        recovery.payment_id = payment.id
        recovery.attempt_count = min(recovery.max_attempts, (recovery.attempt_count or 0) + 1)
        recovery.status = "analyzing"
        await self.recovery_repo.update(recovery)
        await self.recovery_repo.add_audit(
            recovery_id=recovery.id,
            event_type="recovery_attempt_started",
            actor="system",
            action="resume_recovery",
            metadata_={"payment_id": payment.id, "attempt": recovery.attempt_count},
        )
        await self.session.commit()
        await self._run_agent(recovery.id)
        return recovery

    async def pause_recovery(self, recovery_id: int) -> dict:
        recovery = await self.recovery_repo.get_by_id(recovery_id)
        if not recovery:
            return {"recovery_id": recovery_id, "status": "not_found", "message": "Recovery not found"}

        if recovery.status in ("recovered", "exhausted", "escalated", "cancelled", "unsafe_to_retry"):
            return {
                "recovery_id": recovery_id,
                "status": recovery.status,
                "message": f"Recovery already in terminal state '{recovery.status}'; cannot pause.",
            }

        await self.recovery_repo.update(recovery, status="paused")
        await self.recovery_repo.add_audit(
            recovery_id=recovery.id,
            event_type="recovery_paused",
            actor="user",
            action="pause_recovery",
            metadata_={},
        )
        logger.info("recovery_paused", recovery_id=recovery_id)
        return {"recovery_id": recovery_id, "status": "paused", "message": "Recovery paused."}

    async def resume_paused_recovery(self, recovery_id: int) -> dict:
        recovery = await self.recovery_repo.get_by_id(recovery_id)
        if not recovery:
            return {"recovery_id": recovery_id, "status": "not_found", "message": "Recovery not found"}

        if recovery.status != "paused":
            return {
                "recovery_id": recovery_id,
                "status": recovery.status,
                "message": f"Recovery is not paused (status='{recovery.status}').",
            }

        await self.recovery_repo.update(recovery, status="pending")
        await self.recovery_repo.add_audit(
            recovery_id=recovery.id,
            event_type="recovery_resumed",
            actor="user",
            action="resume_recovery",
            metadata_={},
        )
        logger.info("recovery_resumed", recovery_id=recovery_id)
        await self._run_agent(recovery_id)
        return {"recovery_id": recovery_id, "status": "pending", "message": "Recovery resumed."}

    async def review_recovery(
        self,
        recovery_id: int,
        decision: str,
        notes: str | None = None,
        reviewer: str = "operator",
    ) -> dict:
        recovery = await self.recovery_repo.get_by_id(recovery_id)
        if not recovery:
            return {"recovery_id": recovery_id, "status": "not_found", "message": "Recovery not found"}

        if decision == "approve_retry":
            # Human operator overrides risk/ambiguity and approves automated retry
            recovery.status = "analyzing"
            recovery.current_strategy = "notify_retry"
            recovery.current_step = None
            recovery.explanation = f"Human review approved by {reviewer}: {notes or 'Operator authorized recovery retry.'}"
            await self.recovery_repo.update(recovery)
            await self.recovery_repo.add_audit(
                recovery_id=recovery.id,
                event_type="human_review_approved",
                actor=reviewer,
                action="approve_retry",
                metadata_={"notes": notes, "decision": decision},
            )
            await self.session.commit()
            await self._run_agent(recovery_id, operator_override=True)
            return {
                "recovery_id": recovery_id,
                "status": recovery.status,
                "message": "Recovery approved and retry execution initiated.",
            }

        elif decision == "reject":
            # Human operator rejects automated retries and stops the recovery
            recovery.status = "exhausted"
            recovery.explanation = f"Human review rejected by {reviewer}: {notes or 'Operator stopped recovery.'}"
            await self.recovery_repo.update(recovery)
            await self.recovery_repo.add_audit(
                recovery_id=recovery.id,
                event_type="human_review_rejected",
                actor=reviewer,
                action="reject_recovery",
                metadata_={"notes": notes, "decision": decision},
            )
            await self.session.commit()
            return {
                "recovery_id": recovery_id,
                "status": "exhausted",
                "message": "Recovery stopped and marked exhausted per human review.",
            }

        elif decision == "resolve":
            # Human operator confirms payment was collected or resolved manually
            from datetime import datetime, timezone
            recovery.status = "recovered"
            recovery.recovered_at = datetime.now(timezone.utc)
            recovery.explanation = f"Manual resolution confirmed by {reviewer}: {notes or 'Resolved manually by operator.'}"
            await self.recovery_repo.update(recovery)
            payment = await self.payment_repo.get_by_id(recovery.payment_id)
            if payment:
                await self.payment_repo.update(payment, recovered=True, status="captured")
            await self.recovery_repo.add_audit(
                recovery_id=recovery.id,
                event_type="human_review_resolved",
                actor=reviewer,
                action="manual_resolution",
                metadata_={"notes": notes, "decision": decision},
            )
            await self.session.commit()
            return {
                "recovery_id": recovery_id,
                "status": "recovered",
                "message": "Recovery marked as successfully recovered by operator.",
            }

        return {
            "recovery_id": recovery_id,
            "status": recovery.status,
            "message": f"Unknown decision '{decision}'.",
        }

    async def _run_agent(self, recovery_id: int, operator_override: bool = False) -> None:
        from app.agent.graph import RecoveryAgent

        agent = RecoveryAgent(self.session)
        await agent.run(recovery_id, operator_override=operator_override)
        await self.session.commit()
