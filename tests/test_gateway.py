import pytest

from app.core.config import Settings
from app.models.payment import PaymentStatus
from app.services.gateway import SimulatedPaymentGateway


def settings() -> Settings:
    return Settings(
        api_key="test",
        database_url="sqlite+aiosqlite:///:memory:",
        rabbitmq_url="amqp://guest:guest@localhost:5672/",
        processing_min_delay_seconds=2,
        processing_max_delay_seconds=5,
        processing_success_rate=0.9,
    )


async def test_gateway_succeeds_without_real_sleep() -> None:
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    gateway = SimulatedPaymentGateway(
        settings=settings(),
        delay_provider=lambda minimum, maximum: 3.0,
        outcome_provider=lambda: 0.2,
        sleep=sleep,
    )

    assert await gateway.process() is PaymentStatus.SUCCEEDED
    assert delays == [3.0]


async def test_gateway_can_fail_deterministically() -> None:
    async def no_sleep(_: float) -> None:
        return None

    gateway = SimulatedPaymentGateway(
        settings=settings(),
        delay_provider=lambda minimum, maximum: minimum,
        outcome_provider=lambda: 0.95,
        sleep=no_sleep,
    )

    assert await gateway.process() is PaymentStatus.FAILED
