import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.models.outbox import OutboxEvent

PublishEvent = Callable[[dict[str, object]], Awaitable[None]]


class OutboxPublisher:
    """Reliably bridges committed database events into RabbitMQ.

    A transaction lock prevents two workers from publishing the same pending
    event concurrently. `published_at` changes only after RabbitMQ accepts it.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publish: PublishEvent,
        batch_size: int | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.publish = publish
        self.batch_size = batch_size or get_settings().outbox_batch_size

    async def publish_pending(self) -> int:
        async with self.session_factory() as session:
            async with session.begin():
                events = (
                    await session.scalars(
                        select(OutboxEvent)
                        .where(OutboxEvent.published_at.is_(None))
                        .order_by(OutboxEvent.created_at)
                        .limit(self.batch_size)
                        .with_for_update(skip_locked=True)
                    )
                ).all()

                for event in events:
                    await self.publish(event.payload)
                    event.published_at = datetime.now(UTC)

                return len(events)

    async def run_forever(self) -> None:
        settings = get_settings()
        while True:
            published = await self.publish_pending()
            if published == 0:
                await asyncio.sleep(settings.outbox_poll_interval_seconds)
