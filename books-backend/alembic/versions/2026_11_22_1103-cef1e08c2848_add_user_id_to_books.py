"""add user id to books

Revision ID: cef1e08c2848
Revises: f480447515b2
Create Date: 2026-11-22 11:03:55.488778

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cef1e08c2848"
down_revision: str | None = "f480447515b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FOREIGN_KEY_NAME = "fk_books_user_id_users"


def upgrade() -> None:
    """Store the owning user on each book, taken from its user_books row."""
    with op.batch_alter_table("books") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))

    op.execute(
        "UPDATE books SET user_id = "
        "(SELECT user_id FROM user_books WHERE user_books.book_id = books.id)"
    )

    with op.batch_alter_table("books") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(FOREIGN_KEY_NAME, "users", ["user_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("books") as batch_op:
        batch_op.drop_constraint(FOREIGN_KEY_NAME, type_="foreignkey")
        batch_op.drop_column("user_id")
