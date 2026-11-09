from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        return await self.session.scalar(select(Payment).where(Payment.id == payment_id))

    async def get_by_idempotency_key(self, idempotency_key: str) -> Payment | None:
        return await self.session.scalar(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
