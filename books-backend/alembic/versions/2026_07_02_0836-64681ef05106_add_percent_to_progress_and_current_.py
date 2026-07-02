"""add percent to progress and current_percent snapshot

Revision ID: 64681ef05106
Revises: b2c3d4e5f6a7
Create Date: 2026-07-02 08:36:54.843421

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "64681ef05106"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("book_event_progress") as batch_op:
        batch_op.add_column(sa.Column("percent", sa.Numeric(5, 2), nullable=True))
        batch_op.alter_column("page", existing_type=sa.Integer(), nullable=True)
    op.add_column(
        "user_books", sa.Column("current_percent", sa.Numeric(5, 2), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_books", "current_percent")
    with op.batch_alter_table("book_event_progress") as batch_op:
        batch_op.alter_column("page", existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column("percent")
