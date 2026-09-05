from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.customer import Customer
from app.models.payment import Payment
from app.core.logging import get_logger

logger = get_logger("customer_service")


class CustomerService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_customer_history(self, customer_id: int) -> dict:
        """Get customer payment history for recovery scoring."""
        # Total payments
        total_result = await self.session.execute(
            select(func.count()).select_from(Payment).where(Payment.customer_id == customer_id)
        )
        total_payments = total_result.scalar() or 0

        # Successful payments
        success_result = await self.session.execute(
            select(func.count())
            .select_from(Payment)
            .where(Payment.customer_id == customer_id, Payment.status.in_(["captured", "authorized"]))
        )
        successful_payments = success_result.scalar() or 0

        # Failed payments
        fail_result = await self.session.execute(
            select(func.count()).select_from(Payment).where(Payment.customer_id == customer_id, Payment.status == "failed")
        )
        failed_payments = fail_result.scalar() or 0

        # Recent payment amounts
        recent_result = await self.session.execute(
            select(Payment.amount)
            .where(Payment.customer_id == customer_id, Payment.status.in_(["captured", "authorized"]))
            .order_by(Payment.created_at.desc())
            .limit(5)
        )
        recent_amounts = [r for r in recent_result.scalars().all()]

        customer = await self.session.get(Customer, customer_id)

        return {
            "customer_id": customer_id,
            "email": customer.email if customer else None,
            "phone": customer.phone if customer else None,
            "total_payments": total_payments,
            "successful_payments": successful_payments,
            "failed_payments": failed_payments,
            "success_rate": successful_payments / total_payments if total_payments > 0 else 0.0,
            "recent_successful_amounts": recent_amounts,
            "is_returning_customer": total_payments > 1,
            "has_previous_success": successful_payments > 0,
        }