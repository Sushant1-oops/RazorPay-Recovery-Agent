from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.payment import Payment
from app.models.payment_event import PaymentEvent
from app.models.customer import Customer


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_razorpay_id(self, rzp_payment_id: str) -> Payment | None:
        result = await self.session.execute(select(Payment).where(Payment.razorpay_payment_id == rzp_payment_id))
        return result.scalar_one_or_none()

    async def get_by_id(self, payment_id: int) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def create(self, **kwargs) -> Payment:
        payment = Payment(**kwargs)
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def update(self, payment: Payment, **kwargs) -> Payment:
        for key, value in kwargs.items():
            setattr(payment, key, value)
        await self.session.flush()
        return payment

    async def list_payments(self, limit: int = 50, offset: int = 0) -> tuple[list[Payment], int]:
        total_result = await self.session.execute(select(func.count()).select_from(Payment))
        total = total_result.scalar() or 0
        result = await self.session.execute(select(Payment).order_by(Payment.created_at.desc()).limit(limit).offset(offset))
        return list(result.scalars().all()), total

    async def get_or_create_customer(self, external_id: str, email: str | None = None, phone: str | None = None) -> Customer:
        result = await self.session.execute(select(Customer).where(Customer.external_customer_id == external_id))
        customer = result.scalar_one_or_none()
        if customer is None:
            customer = Customer(external_customer_id=external_id, email=email, phone=phone)
            self.session.add(customer)
            await self.session.flush()
        return customer