"""add note event payload table

Revision ID: 48b6f8e64567
Revises: e119fed0558c
Create Date: 2026-01-17 22:50:55.994455

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "48b6f8e64567"
down_revision: Union[str, None] = "e119fed0558c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "book_event_notes",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["book_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    conn = op.get_bind()
    for code in ("note_set",):
        conn.execute(
            sa.text("INSERT OR IGNORE INTO book_event_types (code) VALUES (:code)"),
            {"code": code},
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM book_event_types WHERE code IN (:c1)"),
        {"c1": "note_set"},
    )
    op.drop_table("book_event_notes")
