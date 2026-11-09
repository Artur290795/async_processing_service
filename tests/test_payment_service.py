from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.outbox import OutboxEvent
from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import PaymentCreate
from app.services.payment import PaymentService


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session

    await engine.dispose()


@pytest.fixture
def payload() -> PaymentCreate:
    return PaymentCreate(
        amount=Decimal("12.50"),
        currency="RUB",
        description="Test payment",
        metadata={"order_id": "42"},
        webhook_url="https://example.test/webhooks/payments",
    )


async def test_creates_payment_and_outbox_event_in_one_transaction(session, payload) -> None:
    result = await PaymentService(session).create(payload, "request-42")

    assert result.was_created is True
    assert result.payment.status is PaymentStatus.PENDING

    payments = await session.scalar(select(func.count()).select_from(Payment))
    events = await session.scalars(select(OutboxEvent))
    event = events.one()
    assert payments == 1
    assert event.payment_id == result.payment.id
    assert event.payload == {"payment_id": str(result.payment.id), "version": 1}


async def test_same_idempotency_key_does_not_create_duplicate(session, payload) -> None:
    first = await PaymentService(session).create(payload, "same-key")
    second = await PaymentService(session).create(payload, "same-key")

    assert first.was_created is True
    assert second.was_created is False
    assert second.payment.id == first.payment.id
    assert await session.scalar(select(func.count()).select_from(Payment)) == 1
    assert await session.scalar(select(func.count()).select_from(OutboxEvent)) == 1
