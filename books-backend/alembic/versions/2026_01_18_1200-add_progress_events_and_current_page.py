"""add progress events and current page snapshot

Revision ID: 7c1a2b3d4e5f
Revises: 48b6f8e64567
Create Date: 2026-01-18 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c1a2b3d4e5f"
down_revision: Union[str, None] = "48b6f8e64567"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "book_event_progress",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["book_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.add_column("user_books", sa.Column("current_page", sa.Integer(), nullable=True))
    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT OR IGNORE INTO book_event_types (code) VALUES (:code)"),
        {"code": "progress_set"},
    )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM book_event_types WHERE code IN (:c1)"),
        {"c1": "progress_set"},
    )
    op.drop_column("user_books", "current_page")
    op.drop_table("book_event_progress")
