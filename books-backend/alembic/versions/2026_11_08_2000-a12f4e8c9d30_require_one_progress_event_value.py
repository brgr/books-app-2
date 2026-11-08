"""require exactly one progress event value

Revision ID: a12f4e8c9d30
Revises: 5790d52b17d6
Create Date: 2026-11-08 20:00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "a12f4e8c9d30"
down_revision: str | None = "5790d52b17d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # We arbitrarily chose to retain the page when both values are present.
    # (It's a bit weird in the first place that this was allowed to exist)
    op.execute(
        "UPDATE book_event_progress SET percent = NULL "
        "WHERE page IS NOT NULL AND percent IS NOT NULL"
    )
    op.execute(
        "UPDATE user_books SET current_percent = NULL "
        "WHERE current_page IS NOT NULL AND current_percent IS NOT NULL"
    )

    with op.batch_alter_table("book_event_progress") as batch_op:
        batch_op.create_check_constraint(
            "ck_book_event_progress_exactly_one_value",
            "(page IS NOT NULL AND percent IS NULL) OR "
            "(page IS NULL AND percent IS NOT NULL)",
        )


def downgrade() -> None:
    with op.batch_alter_table("book_event_progress") as batch_op:
        batch_op.drop_constraint(
            "ck_book_event_progress_exactly_one_value", type_="check"
        )
