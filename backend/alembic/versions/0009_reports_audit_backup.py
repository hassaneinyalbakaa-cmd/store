"""add reports audit logs and local backup records

Revision ID: 0009_reports_audit_backup
Revises: 0008_transfers_stocktakes
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0009_reports_audit_backup"
down_revision: Union[str, Sequence[str], None] = "0008_transfers_stocktakes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("user_name", sa.String(length=160), nullable=False),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("action_label", sa.String(length=120), nullable=False),
        sa.Column("document_number", sa.String(length=80), nullable=True),
        sa.Column("details", sa.String(length=500), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "backup_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(length=180), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.UniqueConstraint("filename"),
    )
    op.create_index(
        "ix_backup_records_created_by_id", "backup_records", ["created_by_id"]
    )
    op.create_index("ix_backup_records_created_at", "backup_records", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_backup_records_created_at", table_name="backup_records")
    op.drop_index("ix_backup_records_created_by_id", table_name="backup_records")
    op.drop_table("backup_records")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")