"""enforce issue audit timestamps

Revision ID: 0007_issue_timestamps_not_null
Revises: 0006_issue_requests
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0007_issue_timestamps_not_null"
down_revision: Union[str, Sequence[str], None] = "0006_issue_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "issue_requests",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_server_default=sa.func.now(),
        nullable=False,
    )
    op.alter_column(
        "issue_vouchers",
        "issued_at",
        existing_type=sa.DateTime(timezone=True),
        existing_server_default=sa.func.now(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "issue_vouchers",
        "issued_at",
        existing_type=sa.DateTime(timezone=True),
        existing_server_default=sa.func.now(),
        nullable=True,
    )
    op.alter_column(
        "issue_requests",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_server_default=sa.func.now(),
        nullable=True,
    )