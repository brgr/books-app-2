"""add user book ratings

Revision ID: 9a9417c041cf
Revises: 5dde69bb561c
Create Date: 2026-09-02 22:46:55.654055

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a9417c041cf"
down_revision: Union[str, None] = "5dde69bb561c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add an optional half-star rating for each user's book."""
    op.add_column(
        "user_books",
        sa.Column("rating", sa.Numeric(precision=2, scale=1), nullable=True),
    )


def downgrade() -> None:
    """Remove per-user book ratings."""
    op.drop_column("user_books", "rating")
