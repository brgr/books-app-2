"""Remove price from books table

Revision ID: 9876543210ab
Revises: 8340ac8cc312
Create Date: 2025-10-14 21:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9876543210ab"
down_revision: Union[str, None] = "8340ac8cc312"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("books", "price")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("books", sa.Column("price", sa.Float(), nullable=True))
