"""add warehouse transfers and stocktakes

Revision ID: 0008_transfers_stocktakes
Revises: 0007_issue_timestamps_not_null
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0008_transfers_stocktakes"
down_revision: Union[str, Sequence[str], None] = "0007_issue_timestamps_not_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_transfers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transfer_number", sa.String(length=40), nullable=False),
        sa.Column("source_warehouse_id", sa.Integer(), nullable=False),
        sa.Column("destination_warehouse_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=False, server_default=""),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_by_id", sa.Integer(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_id", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["source_warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["destination_warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["received_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["completed_by_id"], ["users.id"]),
        sa.UniqueConstraint("transfer_number"),
    )
    op.create_index(
        "ix_stock_transfers_source_warehouse_id",
        "stock_transfers",
        ["source_warehouse_id"],
    )
    op.create_index(
        "ix_stock_transfers_destination_warehouse_id",
        "stock_transfers",
        ["destination_warehouse_id"],
    )
    op.create_index("ix_stock_transfers_item_id", "stock_transfers", ["item_id"])
    op.create_index("ix_stock_transfers_status", "stock_transfers", ["status"])
    op.create_index(
        "ix_stock_transfers_created_by_id", "stock_transfers", ["created_by_id"]
    )
    op.create_index(
        "ix_stock_transfers_received_by_id", "stock_transfers", ["received_by_id"]
    )
    op.create_index(
        "ix_stock_transfers_completed_by_id", "stock_transfers", ["completed_by_id"]
    )

    op.create_table(
        "stocktakes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stocktake_number", sa.String(length=40), nullable=False),
        sa.Column("stocktake_type", sa.String(length=20), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("stocktake_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("notes", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("completed_by_id", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["completed_by_id"], ["users.id"]),
        sa.UniqueConstraint("stocktake_number"),
    )
    op.create_index("ix_stocktakes_warehouse_id", "stocktakes", ["warehouse_id"])
    op.create_index("ix_stocktakes_status", "stocktakes", ["status"])
    op.create_index("ix_stocktakes_created_by_id", "stocktakes", ["created_by_id"])
    op.create_index("ix_stocktakes_completed_by_id", "stocktakes", ["completed_by_id"])

    op.create_table(
        "stocktake_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stocktake_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("system_quantity", sa.Float(), nullable=False),
        sa.Column("actual_quantity", sa.Float(), nullable=True),
        sa.Column("difference", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["stocktake_id"], ["stocktakes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.UniqueConstraint("stocktake_id", "item_id", name="uq_stocktake_item"),
    )
    op.create_index(
        "ix_stocktake_lines_stocktake_id", "stocktake_lines", ["stocktake_id"]
    )
    op.create_index("ix_stocktake_lines_item_id", "stocktake_lines", ["item_id"])
    op.create_index(
        "ix_stocktake_lines_warehouse_id", "stocktake_lines", ["warehouse_id"]
    )

    op.create_table(
        "transfer_serials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transfer_id", sa.Integer(), nullable=False),
        sa.Column("serial_id", sa.Integer(), nullable=False),
        sa.Column("serial_number", sa.String(length=160), nullable=False),
        sa.ForeignKeyConstraint(
            ["transfer_id"], ["stock_transfers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["serial_id"], ["inventory_serials.id"]),
        sa.UniqueConstraint("transfer_id", "serial_id", name="uq_transfer_serial"),
    )
    op.create_index("ix_transfer_serials_transfer_id", "transfer_serials", ["transfer_id"])
    op.create_index("ix_transfer_serials_serial_id", "transfer_serials", ["serial_id"])

    op.add_column(
        "inventory_movements",
        sa.Column("transfer_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "inventory_movements",
        sa.Column("stocktake_line_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_inventory_movements_transfer_id",
        "inventory_movements",
        "stock_transfers",
        ["transfer_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_inventory_movements_stocktake_line_id",
        "inventory_movements",
        "stocktake_lines",
        ["stocktake_line_id"],
        ["id"],
    )
    op.create_index(
        "ix_inventory_movements_transfer_id",
        "inventory_movements",
        ["transfer_id"],
    )
    op.create_index(
        "ix_inventory_movements_stocktake_line_id",
        "inventory_movements",
        ["stocktake_line_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inventory_movements_stocktake_line_id", table_name="inventory_movements"
    )
    op.drop_index(
        "ix_inventory_movements_transfer_id", table_name="inventory_movements"
    )
    op.drop_constraint(
        "fk_inventory_movements_stocktake_line_id",
        "inventory_movements",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_inventory_movements_transfer_id",
        "inventory_movements",
        type_="foreignkey",
    )
    op.drop_column("inventory_movements", "stocktake_line_id")
    op.drop_column("inventory_movements", "transfer_id")
    op.drop_table("transfer_serials")
    op.drop_table("stocktake_lines")
    op.drop_table("stocktakes")
    op.drop_table("stock_transfers")