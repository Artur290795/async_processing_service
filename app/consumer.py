import asyncio

from app.broker.topology import PAYMENTS_EXCHANGE, PAYMENTS_QUEUE, broker, declare_topology
from app.db.session import SessionLocal
from app.services.outbox import OutboxPublisher


async def publish_payment_event(payload: dict[str, object]) -> None:
    await broker.publish(
        payload,
        queue=PAYMENTS_QUEUE,
        exchange=PAYMENTS_EXCHANGE,
    )


async def run() -> None:
    """Run broker consumers and the independent outbox publisher in one worker."""
    publisher = OutboxPublisher(SessionLocal, publish_payment_event)
    async with broker:
        await declare_topology()
        await asyncio.gather(broker.start(), publisher.run_forever())


if __name__ == "__main__":
    asyncio.run(run())
