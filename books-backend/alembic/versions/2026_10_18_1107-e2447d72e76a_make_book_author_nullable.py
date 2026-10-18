"""make book author nullable

Revision ID: e2447d72e76a
Revises: f828a240d0a5
Create Date: 2026-10-18 11:07:36.969777

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e2447d72e76a"
down_revision: str | None = "f828a240d0a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow missing authors and normalize existing empty values."""
    with op.batch_alter_table("books") as batch_op:
        batch_op.alter_column("author", existing_type=sa.String(100), nullable=True)
    op.execute("UPDATE books SET author = NULL WHERE author = ''")


def downgrade() -> None:
    """Restore the non-null column using the previous empty-string convention."""
    op.execute("UPDATE books SET author = '' WHERE author IS NULL")
    with op.batch_alter_table("books") as batch_op:
        batch_op.alter_column("author", existing_type=sa.String(100), nullable=False)
