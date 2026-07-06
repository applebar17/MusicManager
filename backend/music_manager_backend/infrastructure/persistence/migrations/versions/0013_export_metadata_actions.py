"""Add export metadata action payloads.

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if _has_column("export_plan_items", "metadata_payload_json"):
        return
    op.add_column(
        "export_plan_items",
        sa.Column("metadata_payload_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    if not _has_column("export_plan_items", "metadata_payload_json"):
        return
    op.drop_column("export_plan_items", "metadata_payload_json")


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))
