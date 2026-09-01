"""add receipts and inventory movement ledger

Revision ID: 0004_inventory_receipts
Revises: 0003_catalog_entities
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_inventory_receipts"
down_revision: Union[str, Sequence[str], None] = "0003_catalog_entities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("receipt_number", sa.String(length=40), nullable=False),
        sa.Column("receipt_date", sa.Date(), nullable=False),
        sa.Column("supplier", sa.String(length=160), nullable=False),
        sa.Column("document_number", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("notes", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("receipt_number"),
    )
    op.create_table(
        "receipt_details",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("receipt_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("storage_location_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["storage_location_id"], ["storage_locations.id"]),
    )
    for column in ("receipt_id", "item_id", "warehouse_id", "storage_location_id"):
        op.create_index(f"ix_receipt_details_{column}", "receipt_details", [column])
    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("movement_date", sa.Date(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("storage_location_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("receipt_detail_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["storage_location_id"], ["storage_locations.id"]),
        sa.ForeignKeyConstraint(["receipt_detail_id"], ["receipt_details.id"]),
        sa.UniqueConstraint("receipt_detail_id"),
    )
    for column in ("movement_type", "item_id", "warehouse_id", "storage_location_id", "receipt_detail_id"):
        op.create_index(f"ix_inventory_movements_{column}", "inventory_movements", [column])
    op.create_table(
        "inventory_serials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("serial_number", sa.String(length=160), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("storage_location_id", sa.Integer(), nullable=True),
        sa.Column("movement_id", sa.Integer(), nullable=False),
        sa.Column("receipt_detail_id", sa.Integer(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["storage_location_id"], ["storage_locations.id"]),
        sa.ForeignKeyConstraint(["movement_id"], ["inventory_movements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receipt_detail_id"], ["receipt_details.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("serial_number"),
    )
    for column in ("item_id", "warehouse_id", "storage_location_id", "movement_id", "receipt_detail_id"):
        op.create_index(f"ix_inventory_serials_{column}", "inventory_serials", [column])


def downgrade() -> None:
    for column in ("item_id", "warehouse_id", "storage_location_id", "movement_id", "receipt_detail_id"):
        op.drop_index(f"ix_inventory_serials_{column}", table_name="inventory_serials")
    op.drop_table("inventory_serials")
    for column in ("movement_type", "item_id", "warehouse_id", "storage_location_id", "receipt_detail_id"):
        op.drop_index(f"ix_inventory_movements_{column}", table_name="inventory_movements")
    op.drop_table("inventory_movements")
    for column in ("receipt_id", "item_id", "warehouse_id", "storage_location_id"):
        op.drop_index(f"ix_receipt_details_{column}", table_name="receipt_details")
    op.drop_table("receipt_details")
    op.drop_table("receipts")