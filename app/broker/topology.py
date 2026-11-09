from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from app.core.config import get_settings

PAYMENTS_EXCHANGE = RabbitExchange("payments", type=ExchangeType.DIRECT, durable=True)
DEAD_LETTER_EXCHANGE = RabbitExchange("payments.dlx", type=ExchangeType.DIRECT, durable=True)

PAYMENTS_QUEUE = RabbitQueue(
    "payments.new",
    durable=True,
    routing_key="payments.new",
    arguments={
        "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE.name,
        "x-dead-letter-routing-key": "payments.dlq",
    },
)
DEAD_LETTER_QUEUE = RabbitQueue(
    "payments.dlq",
    durable=True,
    routing_key="payments.dlq",
)

broker = RabbitBroker(get_settings().rabbitmq_url)


async def declare_topology() -> None:
    """Declare durable exchanges and queues before publishing or consuming."""
    await broker.declare_exchange(PAYMENTS_EXCHANGE)
    await broker.declare_exchange(DEAD_LETTER_EXCHANGE)
    await broker.declare_queue(PAYMENTS_QUEUE, exchange=PAYMENTS_EXCHANGE)
    await broker.declare_queue(DEAD_LETTER_QUEUE, exchange=DEAD_LETTER_EXCHANGE)
