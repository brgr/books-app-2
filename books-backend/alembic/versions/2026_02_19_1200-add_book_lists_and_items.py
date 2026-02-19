"""add book lists and items

Revision ID: c3f1a2b4d5e6
Revises: b6c8a5d1e2f3
Create Date: 2026-02-19 12:00:00.000000

"""

from decimal import Decimal
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3f1a2b4d5e6"
down_revision: Union[str, None] = "b6c8a5d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "book_lists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
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
        "ix_book_list_items_list_sort",
        "book_list_items",
        ["list_id", "sort_order"],
    )

    bind = op.get_bind()
    meta = sa.MetaData()
    users = sa.Table("users", meta, autoload_with=bind)
    user_books = sa.Table("user_books", meta, autoload_with=bind)
    book_lists = sa.Table("book_lists", meta, autoload_with=bind)
    book_list_items = sa.Table("book_list_items", meta, autoload_with=bind)

    default_lists = ("To Read", "Finished")
    to_read_statuses = ("want_to_read", "started", "abandoned")
    finished_statuses = ("finished",)

    user_ids = bind.execute(sa.select(users.c.id)).scalars().all()
    for user_id in user_ids:
        list_ids: dict[str, int] = {}
        for name in default_lists:
            result = bind.execute(
                book_lists.insert().values(user_id=user_id, name=name)
            )
            list_id = None
            if result.inserted_primary_key:
                list_id = result.inserted_primary_key[0]
            if list_id is None:
                list_id = result.lastrowid
            list_ids[name] = int(list_id)

        def _insert_items(list_name: str, statuses: tuple[str, ...]) -> None:
            rows = (
                bind.execute(
                    sa.select(user_books.c.id)
                    .where(
                        user_books.c.user_id == user_id,
                        user_books.c.status.in_(statuses),
                    )
                    .order_by(user_books.c.id.asc())
                )
                .scalars()
                .all()
            )
            for index, user_book_id in enumerate(rows, start=1):
                bind.execute(
                    book_list_items.insert().values(
                        list_id=list_ids[list_name],
                        user_book_id=user_book_id,
                        sort_order=Decimal("1000") * Decimal(index),
                    )
                )

        _insert_items("To Read", to_read_statuses)
        _insert_items("Finished", finished_statuses)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_book_list_items_list_sort", table_name="book_list_items")
    op.drop_table("book_list_items")
    op.drop_table("book_lists")
