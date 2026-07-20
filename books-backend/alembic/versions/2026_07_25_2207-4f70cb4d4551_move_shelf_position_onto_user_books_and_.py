"""move shelf position onto user_books and drop shelf items

Shelf membership is derived from a book's reading status, so it does not need storing.
The one thing shelf_items held that is not derivable is the hand-arranged position, which
moves onto user_books.sort_order; the table then goes.

A book sits on exactly one shelf at a time, so each user_book has at most one shelf_items
row to carry over.

Revision ID: 4f70cb4d4551
Revises: fbadcd8fec48
Create Date: 2026-07-25 22:07:13.442665

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f70cb4d4551"
down_revision: Union[str, None] = "fbadcd8fec48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user_books", sa.Column("sort_order", sa.Numeric(20, 10), nullable=True)
    )
    op.execute(
        "UPDATE user_books SET sort_order = ("
        "  SELECT si.sort_order FROM shelf_items si"
        "  WHERE si.user_book_id = user_books.id"
        ")"
    )

    op.drop_index("ix_shelf_items_shelf_sort", table_name="shelf_items")
    op.drop_table("shelf_items")


def downgrade() -> None:
    """Downgrade schema.

    Rebuilds membership from status, which is where it came from. Books whose shelf row
    is missing are skipped, as there is no shelf to put them on.
    """
    op.create_table(
        "shelf_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "shelf_id",
            sa.Integer(),
            sa.ForeignKey("shelves.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_book_id",
            sa.Integer(),
            sa.ForeignKey("user_books.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Numeric(20, 10), nullable=False),
        sa.UniqueConstraint(
            "shelf_id", "user_book_id", name="uq_shelf_items_shelf_user_book"
        ),
    )
    op.create_index(
        "ix_shelf_items_shelf_sort", "shelf_items", ["shelf_id", "sort_order"]
    )

    # ``status`` is a SQLAlchemy Enum column, so it holds the member NAME (FINISHED),
    # not its value (finished).
    op.execute(
        "INSERT INTO shelf_items (shelf_id, user_book_id, sort_order) "
        "SELECT s.id, ub.id, ub.sort_order "
        "FROM user_books ub "
        "JOIN shelves s ON s.user_id = ub.user_id AND s.name = ("
        "  CASE WHEN ub.status = 'FINISHED' THEN 'Finished' ELSE 'To Read' END"
        ") "
        "WHERE ub.sort_order IS NOT NULL"
    )

    op.drop_column("user_books", "sort_order")
