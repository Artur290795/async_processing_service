from uuid import UUID

from pydantic import BaseModel

from app.broker.topology import PAYMENTS_EXCHANGE, PAYMENTS_QUEUE, broker
from app.db.session import SessionLocal
from app.services.processing import PaymentProcessingService


class PaymentCreatedEvent(BaseModel):
    payment_id: UUID
    version: int


@broker.subscriber(PAYMENTS_QUEUE, exchange=PAYMENTS_EXCHANGE, retry=3)
async def process_payment_event(event: PaymentCreatedEvent) -> None:
    """Retries unexpected processing/webhook failures; exhausted messages go to DLQ."""
    async with SessionLocal() as session:
        await PaymentProcessingService(session).process(event.payment_id)
