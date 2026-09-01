"""remove redundant movement detail index

Revision ID: 0005_remove_detail_index
Revises: 0004_inventory_receipts
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0005_remove_detail_index"
down_revision: Union[str, Sequence[str], None] = "0004_inventory_receipts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(
        "ix_inventory_movements_receipt_detail_id",
        table_name="inventory_movements",
    )


def downgrade() -> None:
    op.create_index(
        "ix_inventory_movements_receipt_detail_id",
        "inventory_movements",
        ["receipt_detail_id"],
    )