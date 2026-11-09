from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent
from app.models.payment import Payment, PaymentStatus
from app.repositories.payment import PaymentRepository
from app.schemas.payment import PaymentCreate


@dataclass(frozen=True)
class CreatePaymentResult:
    payment: Payment
    was_created: bool


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = PaymentRepository(session)

    async def create(self, payload: PaymentCreate, idempotency_key: str) -> CreatePaymentResult:
        """Create a payment and its event atomically, returning an existing idempotent request."""
        try:
            async with self.session.begin():
                existing = await self.repository.get_by_idempotency_key(idempotency_key)
                if existing is not None:
                    return CreatePaymentResult(payment=existing, was_created=False)

                payment = Payment(
                    amount=payload.amount,
                    currency=payload.currency,
                    description=payload.description,
                    metadata_=payload.metadata,
                    status=PaymentStatus.PENDING,
                    idempotency_key=idempotency_key,
                    webhook_url=str(payload.webhook_url),
                )
                self.session.add(payment)
                await self.session.flush()
                await self.session.refresh(payment)

                self.session.add(
                    OutboxEvent(
                        payment_id=payment.id,
                        event_type="payment.created.v1",
                        payload={"payment_id": str(payment.id), "version": 1},
                    )
                )
                await self.session.flush()

            return CreatePaymentResult(payment=payment, was_created=True)
        except IntegrityError:
            # The unique index remains the final guard when identical requests race.
            existing = await self.repository.get_by_idempotency_key(idempotency_key)
            if existing is None:
                raise
            return CreatePaymentResult(payment=existing, was_created=False)

    async def get(self, payment_id: UUID) -> Payment | None:
        return await self.repository.get_by_id(payment_id)
