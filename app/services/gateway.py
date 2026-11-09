import asyncio
import random
from collections.abc import Awaitable, Callable

from app.core.config import Settings, get_settings
from app.models.payment import PaymentStatus


class SimulatedPaymentGateway:
    """A replaceable external payment gateway emulator."""

    def __init__(
        self,
        settings: Settings | None = None,
        delay_provider: Callable[[float, float], float] = random.uniform,
        outcome_provider: Callable[[], float] = random.random,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.settings = settings or get_settings()
        self.delay_provider = delay_provider
        self.outcome_provider = outcome_provider
        self.sleep = sleep

    async def process(self) -> PaymentStatus:
        await self.sleep(
            self.delay_provider(
                self.settings.processing_min_delay_seconds,
                self.settings.processing_max_delay_seconds,
            )
        )
        if self.outcome_provider() < self.settings.processing_success_rate:
            return PaymentStatus.SUCCEEDED
        return PaymentStatus.FAILED
