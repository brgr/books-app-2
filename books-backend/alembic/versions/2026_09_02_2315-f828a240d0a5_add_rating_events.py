"""add rating events

Revision ID: f828a240d0a5
Revises: 9a9417c041cf
Create Date: 2026-09-02 23:15:25.453314

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f828a240d0a5"
down_revision: Union[str, None] = "9a9417c041cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add rating payloads and the rating-set event type."""
    op.create_table(
        "book_event_ratings",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("rating", sa.Numeric(precision=2, scale=1), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["book_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.get_bind().execute(
        sa.text("INSERT OR IGNORE INTO book_event_types (code) VALUES (:code)"),
        {"code": "rating_set"},
    )


def downgrade() -> None:
    """Remove rating event storage and its type."""
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM book_events WHERE event_type_id IN "
            "(SELECT id FROM book_event_types WHERE code = :code)"
        ),
        {"code": "rating_set"},
    )
    conn.execute(
        sa.text("DELETE FROM book_event_types WHERE code = :code"),
        {"code": "rating_set"},
    )
    op.drop_table("book_event_ratings")
