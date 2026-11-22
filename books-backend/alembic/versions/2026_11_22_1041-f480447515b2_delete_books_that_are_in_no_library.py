"""delete books that are in no library

Revision ID: f480447515b2
Revises: ef1874b394f8
Create Date: 2026-11-22 10:41:39.649594

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f480447515b2"
down_revision: str | None = "ef1874b394f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Delete books left behind after being removed from their library."""
    op.execute("DELETE FROM books WHERE id NOT IN (SELECT book_id FROM user_books)")


def downgrade() -> None:
    """Deleted books cannot be restored."""
