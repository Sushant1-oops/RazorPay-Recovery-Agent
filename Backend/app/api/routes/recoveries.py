from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user
from app.repositories.recovery_repository import RecoveryRepository
from app.services.recovery_service import RecoveryService
from app.schemas.recovery import (
    RecoveryResponse,
    RecoveryListResponse,
    RecoveryPauseResponse,
    HumanReviewRequest,
    HumanReviewResponse,
)
from app.models.user import User

router = APIRouter(prefix="/api/v1/recoveries", tags=["Recoveries"])


@router.get("", response_model=RecoveryListResponse)
async def list_recoveries(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repo = RecoveryRepository(db)
    recoveries, total = await repo.list_recoveries(limit=limit, offset=offset)
    return RecoveryListResponse(
        recoveries=[RecoveryResponse.model_validate(r) for r in recoveries],
        total=total,
    )


@router.get("/{recovery_id}", response_model=RecoveryResponse)
async def get_recovery(
    recovery_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repo = RecoveryRepository(db)
    recovery = await repo.get_by_id(recovery_id)
    if not recovery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery not found")
    return RecoveryResponse.model_validate(recovery)


@router.post("/{recovery_id}/pause", response_model=RecoveryPauseResponse)
async def pause_recovery(
    recovery_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = RecoveryService(db)
    result = await svc.pause_recovery(recovery_id)
    await db.commit()
    return RecoveryPauseResponse(**result)


@router.post("/{recovery_id}/resume", response_model=RecoveryPauseResponse)
async def resume_recovery(
    recovery_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = RecoveryService(db)
    result = await svc.resume_paused_recovery(recovery_id)
    await db.commit()
    return RecoveryPauseResponse(**result)


@router.post("/{recovery_id}/review", response_model=HumanReviewResponse)
async def review_recovery(
    recovery_id: int,
    body: HumanReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.decision not in ("approve_retry", "reject", "resolve"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision '{body.decision}'. Must be approve_retry, reject, or resolve.",
        )
    svc = RecoveryService(db)
    result = await svc.review_recovery(
        recovery_id=recovery_id,
        decision=body.decision,
        notes=body.notes,
        reviewer=user.email or "operator",
    )
    if result.get("status") == "not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery not found")
    await db.commit()
    return HumanReviewResponse(**result)