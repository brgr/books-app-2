"""drop user_books

Revision ID: 4722196e8bda
Revises: db180c6e3e54
Create Date: 2026-11-22 22:09:36.220493

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4722196e8bda"
down_revision: str | None = "db180c6e3e54"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("user_books")


def downgrade() -> None:
    op.create_table(
        "user_books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Every book is in exactly one library, its owner's
    op.execute(
        "INSERT INTO user_books (id, user_id, book_id) SELECT id, user_id, id FROM books"
    )
