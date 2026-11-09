"""Track webhook delivery attempts.

Revision ID: 0002_webhook_delivery_state
Revises: 0001_initial
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_webhook_delivery_state"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("webhook_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("payments", sa.Column("webhook_delivered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payments", sa.Column("webhook_last_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "webhook_last_error")
    op.drop_column("payments", "webhook_delivered_at")
    op.drop_column("payments", "webhook_attempts")
