from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.outbox import OutboxEvent
from app.models.payment import Payment, PaymentStatus
from app.services.outbox import OutboxPublisher


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def add_event(session_factory) -> OutboxEvent:
    payment_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            payment = Payment(
                id=payment_id,
                amount="10.00",
                currency="RUB",
                description="outbox test",
                metadata_={},
                status=PaymentStatus.PENDING,
                idempotency_key="outbox-test",
                webhook_url="https://example.test/hook",
            )
            event = OutboxEvent(
                payment_id=payment_id,
                event_type="payment.created.v1",
                payload={"payment_id": str(payment_id), "version": 1},
            )
            session.add_all([payment, event])
        return event


async def test_marks_event_published_only_after_successful_publish(session_factory) -> None:
    event = await add_event(session_factory)
    sent: list[dict[str, object]] = []

    async def publish(payload: dict[str, object]) -> None:
        sent.append(payload)

    assert await OutboxPublisher(session_factory, publish).publish_pending() == 1
    assert sent == [{"payment_id": str(event.payment_id), "version": 1}]

    async with session_factory() as session:
        stored = await session.scalar(select(OutboxEvent).where(OutboxEvent.id == event.id))
        assert stored is not None
        assert stored.published_at is not None


async def test_failed_publish_leaves_event_pending(session_factory) -> None:
    event = await add_event(session_factory)

    async def publish(_: dict[str, object]) -> None:
        raise ConnectionError("RabbitMQ unavailable")

    with pytest.raises(ConnectionError, match="unavailable"):
        await OutboxPublisher(session_factory, publish).publish_pending()

    async with session_factory() as session:
        stored = await session.scalar(select(OutboxEvent).where(OutboxEvent.id == event.id))
        assert stored is not None
        assert stored.published_at is None
