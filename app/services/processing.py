from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import PaymentStatus
from app.repositories.payment import PaymentRepository
from app.services.gateway import SimulatedPaymentGateway
from app.services.webhook import WebhookDispatcher


class PaymentProcessingService:
    def __init__(
        self,
        session: AsyncSession,
        gateway: SimulatedPaymentGateway | None = None,
        webhook_dispatcher: WebhookDispatcher | None = None,
    ) -> None:
        self.session = session
        self.repository = PaymentRepository(session)
        self.gateway = gateway or SimulatedPaymentGateway()
        self.webhook_dispatcher = webhook_dispatcher or WebhookDispatcher(session)

    async def process(self, payment_id: UUID) -> None:
        payment = await self.repository.get_by_id(payment_id)
        if payment is None:
            raise ValueError(f"Payment {payment_id} does not exist")
        await self.session.commit()

        if payment.status is PaymentStatus.PENDING:
            outcome = await self.gateway.process()
            async with self.session.begin():
                locked_payment = await self.repository.get_by_id_for_update(payment_id)
                if locked_payment is None:
                    raise ValueError(f"Payment {payment_id} does not exist")
                if locked_payment.status is PaymentStatus.PENDING:
                    locked_payment.status = outcome
                    locked_payment.processed_at = datetime.now(UTC)

        await self.webhook_dispatcher.deliver(payment_id)
