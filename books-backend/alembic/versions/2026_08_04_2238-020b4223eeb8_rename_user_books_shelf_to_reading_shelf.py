"""rename user_books.shelf to reading_shelf

This column means one of the default shelves, i.e., the reading shelf.
Once we introduce custom shelves later, this will get confusing a bit, so we rename it to be more explicit.

Revision ID: 020b4223eeb8
Revises: cfe2b6015bf1
Create Date: 2026-08-04 22:38:18.050488

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "020b4223eeb8"
down_revision: Union[str, None] = "cfe2b6015bf1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("user_books", "shelf", new_column_name="reading_shelf")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("user_books", "reading_shelf", new_column_name="shelf")
