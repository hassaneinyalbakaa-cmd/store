"""add warehouses departments storage locations and items

Revision ID: 0003_catalog_entities
Revises: 0002_unique_indexes
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_catalog_entities"
down_revision: Union[str, Sequence[str], None] = "0002_unique_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("warehouse_type", sa.String(length=20), nullable=False, server_default="branch"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "storage_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("area", sa.String(length=80), nullable=False),
        sa.Column("shelf", sa.String(length=80), nullable=False),
        sa.Column("bin", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "warehouse_id", "area", "shelf", "bin",
            name="uq_storage_location_coordinates",
        ),
    )
    op.create_index("ix_storage_locations_warehouse_id", "storage_locations", ["warehouse_id"])
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("category", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("unit", sa.String(length=60), nullable=False),
        sa.Column("part_number", sa.String(length=120), nullable=True),
        sa.Column("minimum_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("storage_location_id", sa.Integer(), nullable=True),
        sa.Column("requires_serial_number", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_expiry_date", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["storage_location_id"], ["storage_locations.id"]),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_items_warehouse_id", "items", ["warehouse_id"])
    op.create_index("ix_items_storage_location_id", "items", ["storage_location_id"])


def downgrade() -> None:
    op.drop_index("ix_items_storage_location_id", table_name="items")
    op.drop_index("ix_items_warehouse_id", table_name="items")
    op.drop_table("items")
    op.drop_index("ix_storage_locations_warehouse_id", table_name="storage_locations")
    op.drop_table("storage_locations")
    op.drop_table("departments")
    op.drop_table("warehouses")