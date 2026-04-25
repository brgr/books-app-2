"""add cover_changed event type and payload table

Revision ID: a1b2c3d4e5f6
Revises: e1f2a3b4c5d6
Create Date: 2026-04-25 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "book_event_covers",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("old_cover_image_url", sa.String(length=500), nullable=True),
        sa.Column("new_cover_image_url", sa.String(length=500), nullable=True),
        sa.Column("old_cover_thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("new_cover_thumbnail_url", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["book_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT OR IGNORE INTO book_event_types (code) VALUES (:code)"),
        {"code": "cover_changed"},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM book_event_types WHERE code = :code"),
        {"code": "cover_changed"},
    )
    op.drop_table("book_event_covers")
