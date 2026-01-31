"""add cover thumbnail url to books table

Revision ID: b6c8a5d1e2f3
Revises: 7c1a2b3d4e5f
Create Date: 2026-01-30 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6c8a5d1e2f3"
down_revision: Union[str, None] = "7c1a2b3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "books", sa.Column("cover_thumbnail_url", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("books", "cover_thumbnail_url")
