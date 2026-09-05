from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentResponse, PaymentListResponse
from app.models.user import User

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.get("", response_model=PaymentListResponse)
async def list_payments(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repo = PaymentRepository(db)
    payments, total = await repo.list_payments(limit=limit, offset=offset)
    return PaymentListResponse(payments=[PaymentResponse.model_validate(p) for p in payments], total=total)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repo = PaymentRepository(db)
    payment = await repo.get_by_id(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return PaymentResponse.model_validate(payment)