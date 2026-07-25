"""drop custom book lists

Removes every list that is not one of the two defaults ("To Read", "Finished").
Custom lists came only from the Reading List import, but we currently don't really use or have lists.
We want to have something called shelves soon, and then later maybe also collections.
To get to shelves, we currently simply only take the two default lists.

Revision ID: c4e1a7d38b02
Revises: 60da3ebef996
Create Date: 2026-07-25 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e1a7d38b02"
down_revision: Union[str, None] = "60da3ebef996"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_LIST_NAMES = ("To Read", "Finished")


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    meta = sa.MetaData()
    book_lists = sa.Table("book_lists", meta, autoload_with=bind)
    book_list_items = sa.Table("book_list_items", meta, autoload_with=bind)

    custom_list_ids = sa.select(book_lists.c.id).where(
        book_lists.c.name.notin_(DEFAULT_LIST_NAMES)
    )

    # Delete items explicitly rather than relying on ON DELETE CASCADE, which SQLite only honors
    # when foreign keys are enabled on the connection.
    bind.execute(
        book_list_items.delete().where(
            book_list_items.c.list_id.in_(custom_list_ids.scalar_subquery())
        )
    )
    bind.execute(
        book_lists.delete().where(book_lists.c.name.notin_(DEFAULT_LIST_NAMES))
    )


def downgrade() -> None:
    """Downgrade schema.

    Custom lists are user data with no other source, so they cannot be reconstructed.
    """
    pass
