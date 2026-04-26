"""add imports table and book_event_import_sources sidecar

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-26 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "book_event_import_sources",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["book_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["import_id"], ["imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )


def downgrade() -> None:
    op.drop_table("book_event_import_sources")
    op.drop_table("imports")
