"""Add cover_image_url to books table

Revision ID: 8340ac8cc312
Revises: 1d012f679eaa
Create Date: 2025-10-14 20:49:40.773684

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8340ac8cc312"
down_revision: Union[str, None] = "1d012f679eaa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "books", sa.Column("cover_image_url", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("books", "cover_image_url")
