"""drop user_book reading date columns (started_at/finished_at)

These are now derived from the started_reading / finished_reading events
(project_user_book_state) rather than persisted on user_books.

Revision ID: 60da3ebef996
Revises: 64681ef05106
Create Date: 2026-07-11 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "60da3ebef996"
down_revision: Union[str, None] = "64681ef05106"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the persisted reading-date columns; the values live in events."""
    op.drop_column("user_books", "finished_at")
    op.drop_column("user_books", "started_at")


def downgrade() -> None:
    """Re-add the columns and backfill from the event stream."""
    op.add_column("user_books", sa.Column("started_at", sa.DateTime(), nullable=True))
    op.add_column("user_books", sa.Column("finished_at", sa.DateTime(), nullable=True))

    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE user_books SET started_at = ("
            "  SELECT MAX(be.occurred_at) FROM book_events be"
            "  JOIN book_event_types bet ON be.event_type_id = bet.id"
            "  WHERE be.user_book_id = user_books.id"
            "    AND bet.code = 'started_reading'"
            ")"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE user_books SET finished_at = ("
            "  SELECT MAX(be.occurred_at) FROM book_events be"
            "  JOIN book_event_types bet ON be.event_type_id = bet.id"
            "  WHERE be.user_book_id = user_books.id"
            "    AND bet.code = 'finished_reading'"
            ")"
        )
    )
