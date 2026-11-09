import asyncio
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.repositories.payment import PaymentRepository


class WebhookDeliveryError(RuntimeError):
    pass


class WebhookDispatcher:
    """Send a final payment result at most three times with persisted state."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.repository = PaymentRepository(session)
        self.settings = settings or get_settings()

    async def deliver(self, payment_id: UUID) -> None:
        maximum_attempts = len(self.settings.retry_delays)
        while True:
            async with self.session.begin():
                payment = await self.repository.get_by_id_for_update(payment_id)
                if payment is None:
                    raise WebhookDeliveryError(f"Payment {payment_id} does not exist")
                if payment.webhook_delivered_at is not None:
                    return
                if payment.webhook_attempts >= maximum_attempts:
                    raise WebhookDeliveryError(
                        f"Webhook delivery exhausted {maximum_attempts} attempts for payment {payment_id}"
                    )

                payment.webhook_attempts += 1
                attempt = payment.webhook_attempts
                url = payment.webhook_url
                body = {
                    "payment_id": str(payment.id),
                    "amount": str(payment.amount),
                    "currency": payment.currency,
                    "status": payment.status.value,
                    "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
                }

            try:
                async with httpx.AsyncClient(timeout=self.settings.webhook_timeout_seconds) as client:
                    response = await client.post(url, json=body)
                    response.raise_for_status()
            except httpx.HTTPError as error:
                async with self.session.begin():
                    payment = await self.repository.get_by_id_for_update(payment_id)
                    if payment is not None:
                        payment.webhook_last_error = str(error)[:2_000]

                if attempt >= maximum_attempts:
                    raise WebhookDeliveryError(
                        f"Webhook delivery failed after {maximum_attempts} attempts"
                    ) from error
                await asyncio.sleep(self.settings.retry_delays[attempt - 1])
            else:
                async with self.session.begin():
                    payment = await self.repository.get_by_id_for_update(payment_id)
                    if payment is not None:
                        payment.webhook_delivered_at = datetime.now(UTC)
                        payment.webhook_last_error = None
                return
