"""add imprecise reading dates

Revision ID: 5dde69bb561c
Revises: 9326093bcbca
Create Date: 2026-08-31 19:33:02.648957

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5dde69bb561c"
down_revision: Union[str, None] = "9326093bcbca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Alembic's generated reading-date payload table."""
    op.create_table(
        "book_event_reading_dates",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("value", sa.DateTime(), nullable=True),
        sa.Column(
            "precision",
            sa.Enum("DAY", "MONTH", "YEAR", "UNKNOWN", name="reading_date_precision"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["book_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )

    # Current start/finish timestamps were exact in the old model.  Preserve
    # them as day-precision payloads without changing outward projections.
    op.execute(
        "INSERT INTO book_event_reading_dates (event_id, value, precision) "
        "SELECT be.id, be.occurred_at, 'DAY' "
        "FROM book_events be "
        "JOIN book_event_types bet ON bet.id = be.event_type_id "
        "WHERE bet.code IN ('started_reading', 'finished_reading')"
    )


def downgrade() -> None:
    """Remove the reading-date payload table."""
    op.drop_table("book_event_reading_dates")
    sa.Enum(name="reading_date_precision").drop(op.get_bind(), checkfirst=True)
