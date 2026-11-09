from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_session
from app.schemas.payment import PaymentAccepted, PaymentCreate, PaymentDetail
from app.services.payment import PaymentService

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[Depends(require_api_key)],
)


def to_detail(payment) -> PaymentDetail:
    return PaymentDetail(
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata=payment.metadata_,
        status=payment.status.value,
        webhook_url=payment.webhook_url,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )


@router.post("", response_model=PaymentAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_payment(
    payload: PaymentCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=255),
    session: AsyncSession = Depends(get_session),
) -> PaymentAccepted:
    result = await PaymentService(session).create(payload, idempotency_key)
    payment = result.payment
    return PaymentAccepted(
        payment_id=payment.id,
        status=payment.status.value,
        created_at=payment.created_at,
    )


@router.get("/{payment_id}", response_model=PaymentDetail)
async def get_payment(
    payment_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> PaymentDetail:
    payment = await PaymentService(session).get(payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return to_detail(payment)
