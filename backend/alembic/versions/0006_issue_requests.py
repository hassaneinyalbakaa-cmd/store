"""add issue requests and issue vouchers

Revision ID: 0006_issue_requests
Revises: 0005_remove_detail_index
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0006_issue_requests"
down_revision: Union[str, Sequence[str], None] = "0005_remove_detail_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "issue_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_number", sa.String(length=40), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("request_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.UniqueConstraint("request_number"),
    )
    for column in ("department_id", "item_id", "status", "created_by_id"):
        op.create_index(f"ix_issue_requests_{column}", "issue_requests", [column])

    op.create_table(
        "issue_vouchers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issue_number", sa.String(length=40), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("issued_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["request_id"], ["issue_requests.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["issued_by_id"], ["users.id"]),
        sa.UniqueConstraint("issue_number"),
        sa.UniqueConstraint("request_id"),
    )
    for column in ("item_id", "warehouse_id", "issued_by_id"):
        op.create_index(f"ix_issue_vouchers_{column}", "issue_vouchers", [column])

    op.add_column(
        "inventory_movements",
        sa.Column("issue_voucher_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_inventory_movements_issue_voucher",
        "inventory_movements",
        "issue_vouchers",
        ["issue_voucher_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_inventory_movement_issue_voucher_id",
        "inventory_movements",
        ["issue_voucher_id"],
    )

    op.add_column(
        "inventory_serials",
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "inventory_serials",
        sa.Column("issue_voucher_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_inventory_serials_is_available", "inventory_serials", ["is_available"]
    )
    op.create_index(
        "ix_inventory_serials_issue_voucher_id",
        "inventory_serials",
        ["issue_voucher_id"],
    )
    op.create_foreign_key(
        "fk_inventory_serials_issue_voucher",
        "inventory_serials",
        "issue_vouchers",
        ["issue_voucher_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_inventory_serials_issue_voucher", "inventory_serials", type_="foreignkey"
    )
    op.drop_index("ix_inventory_serials_issue_voucher_id", table_name="inventory_serials")
    op.drop_index("ix_inventory_serials_is_available", table_name="inventory_serials")
    op.drop_column("inventory_serials", "issue_voucher_id")
    op.drop_column("inventory_serials", "is_available")

    op.drop_constraint(
        "uq_inventory_movement_issue_voucher_id",
        "inventory_movements",
        type_="unique",
    )
    op.drop_constraint(
        "fk_inventory_movements_issue_voucher",
        "inventory_movements",
        type_="foreignkey",
    )
    op.drop_column("inventory_movements", "issue_voucher_id")

    for column in ("item_id", "warehouse_id", "issued_by_id"):
        op.drop_index(f"ix_issue_vouchers_{column}", table_name="issue_vouchers")
    op.drop_table("issue_vouchers")

    for column in ("department_id", "item_id", "status", "created_by_id"):
        op.drop_index(f"ix_issue_requests_{column}", table_name="issue_requests")
    op.drop_table("issue_requests")