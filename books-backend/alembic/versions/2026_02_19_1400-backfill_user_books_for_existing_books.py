"""backfill user_books for existing books

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-02-19 14:00:00.000000

"""

from datetime import datetime, UTC
from decimal import Decimal
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    meta = sa.MetaData()
    users = sa.Table("users", meta, autoload_with=bind)
    books = sa.Table("books", meta, autoload_with=bind)
    user_books = sa.Table("user_books", meta, autoload_with=bind)
    book_lists = sa.Table("book_lists", meta, autoload_with=bind)
    book_list_items = sa.Table("book_list_items", meta, autoload_with=bind)
    book_event_types = sa.Table("book_event_types", meta, autoload_with=bind)
    book_events = sa.Table("book_events", meta, autoload_with=bind)

    event_type_id = bind.execute(
        sa.select(book_event_types.c.id).where(
            book_event_types.c.code == "added_to_library"
        )
    ).scalar()
    if event_type_id is None:
        raise RuntimeError("book_event_types must include 'added_to_library'")

    default_list_name = "To Read"

    user_ids = bind.execute(sa.select(users.c.id)).scalars().all()
    for user_id in user_ids:
        list_id = bind.execute(
            sa.select(book_lists.c.id).where(
                book_lists.c.user_id == user_id,
                book_lists.c.name == default_list_name,
            )
        ).scalar()
        if list_id is None:
            result = bind.execute(
                book_lists.insert().values(user_id=user_id, name=default_list_name)
            )
            if result.inserted_primary_key:
                list_id = result.inserted_primary_key[0]
            else:
                list_id = result.lastrowid
        list_id = int(list_id)

        max_sort = bind.execute(
            sa.select(sa.func.max(book_list_items.c.sort_order)).where(
                book_list_items.c.list_id == list_id
            )
        ).scalar()
        next_sort = Decimal(max_sort or 0) + Decimal("1000")

        missing_books = (
            bind.execute(
                sa.select(books.c.id)
                .select_from(
                    books.outerjoin(
                        user_books,
                        sa.and_(
                            user_books.c.book_id == books.c.id,
                            user_books.c.user_id == user_id,
                        ),
                    )
                )
                .where(user_books.c.id.is_(None))
                .order_by(books.c.id.asc())
            )
            .scalars()
            .all()
        )

        for book_id in missing_books:
            result = bind.execute(
                user_books.insert().values(
                    user_id=user_id,
                    book_id=book_id,
                    status="WANT_TO_READ",
                )
            )
            if result.inserted_primary_key:
                user_book_id = result.inserted_primary_key[0]
            else:
                user_book_id = result.lastrowid

            bind.execute(
                book_events.insert().values(
                    id=str(uuid.uuid4()),
                    user_book_id=user_book_id,
                    event_type_id=event_type_id,
                    occurred_at=datetime.now(UTC),
                )
            )

            bind.execute(
                book_list_items.insert().values(
                    list_id=list_id,
                    user_book_id=user_book_id,
                    sort_order=next_sort,
                )
            )
            next_sort += Decimal("1000")


def downgrade() -> None:
    """Downgrade schema."""
    # Data migration only; no-op on downgrade.
    pass
