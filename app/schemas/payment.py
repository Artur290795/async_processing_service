from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: Literal["RUB", "USD", "EUR"]
    description: str = Field(min_length=1, max_length=10_000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: AnyHttpUrl


class PaymentAccepted(BaseModel):
    payment_id: UUID
    status: str
    created_at: datetime


class PaymentDetail(PaymentAccepted):
    model_config = ConfigDict(from_attributes=True)

    amount: Decimal
    currency: str
    description: str
    metadata: dict[str, Any]
    webhook_url: str
    processed_at: datetime | None
