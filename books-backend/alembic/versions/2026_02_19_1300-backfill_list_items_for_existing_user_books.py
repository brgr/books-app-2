"""backfill list items for existing user books

Revision ID: d4e5f6a7b8c9
Revises: c3f1a2b4d5e6
Create Date: 2026-02-19 13:00:00.000000

"""

from decimal import Decimal
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3f1a2b4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    meta = sa.MetaData()
    users = sa.Table("users", meta, autoload_with=bind)
    user_books = sa.Table("user_books", meta, autoload_with=bind)
    book_lists = sa.Table("book_lists", meta, autoload_with=bind)
    book_list_items = sa.Table("book_list_items", meta, autoload_with=bind)

    default_lists = ("To Read", "Finished")
    to_read_statuses = (
        "want_to_read",
        "started",
        "abandoned",
        "WANT_TO_READ",
        "STARTED",
        "ABANDONED",
    )
    finished_statuses = ("finished", "FINISHED")

    user_ids = bind.execute(sa.select(users.c.id)).scalars().all()
    for user_id in user_ids:
        list_ids: dict[str, int] = {}
        for name in default_lists:
            list_id = bind.execute(
                sa.select(book_lists.c.id).where(
                    book_lists.c.user_id == user_id,
                    book_lists.c.name == name,
                )
            ).scalar()
            if list_id is None:
                result = bind.execute(
                    book_lists.insert().values(user_id=user_id, name=name)
                )
                if result.inserted_primary_key:
                    list_id = result.inserted_primary_key[0]
                else:
                    list_id = result.lastrowid
            list_ids[name] = int(list_id)

        def _existing_user_books(list_id: int) -> set[int]:
            rows = (
                bind.execute(
                    sa.select(book_list_items.c.user_book_id).where(
                        book_list_items.c.list_id == list_id
                    )
                )
                .scalars()
                .all()
            )
            return {int(row) for row in rows}

        def _insert_items(list_name: str, statuses: tuple[str, ...]) -> None:
            existing = _existing_user_books(list_ids[list_name])
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
                if int(user_book_id) in existing:
                    continue
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
    # Data migration only; no-op on downgrade.
    pass
