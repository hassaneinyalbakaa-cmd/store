"""remove duplicate indexes covered by unique constraints

Revision ID: 0002_remove_duplicate_unique_indexes
Revises: 0001_initial
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0002_unique_indexes"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_index("ix_users_username", table_name="users")


def downgrade() -> None:
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=False)
    op.create_index("ix_roles_name", "roles", ["name"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=False)