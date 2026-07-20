"""rename book lists to shelves

Rename book_lists -> shelves and book_list_items -> shelf_items (list_id -> shelf_id).

Revision ID: fbadcd8fec48
Revises: c4e1a7d38b02
Create Date: 2026-07-25 20:00:27.654612

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fbadcd8fec48"
down_revision: Union[str, None] = "c4e1a7d38b02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "shelves",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_shelves_user_name"),
    )
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

    op.execute(
        "INSERT INTO shelves (id, user_id, name) SELECT id, user_id, name FROM book_lists"
    )
    op.execute(
        "INSERT INTO shelf_items (id, shelf_id, user_book_id, sort_order) "
        "SELECT id, list_id, user_book_id, sort_order FROM book_list_items"
    )

    op.drop_index("ix_book_list_items_list_sort", table_name="book_list_items")
    op.drop_table("book_list_items")
    op.drop_table("book_lists")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "book_lists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_book_lists_user_name"),
    )
    op.create_table(
        "book_list_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "list_id",
            sa.Integer(),
            sa.ForeignKey("book_lists.id", ondelete="CASCADE"),
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
            "list_id", "user_book_id", name="uq_book_list_items_list_user_book"
        ),
    )
    op.create_index(
        "ix_book_list_items_list_sort", "book_list_items", ["list_id", "sort_order"]
    )

    op.execute(
        "INSERT INTO book_lists (id, user_id, name) SELECT id, user_id, name FROM shelves"
    )
    op.execute(
        "INSERT INTO book_list_items (id, list_id, user_book_id, sort_order) "
        "SELECT id, shelf_id, user_book_id, sort_order FROM shelf_items"
    )

    op.drop_index("ix_shelf_items_shelf_sort", table_name="shelf_items")
    op.drop_table("shelf_items")
    op.drop_table("shelves")
