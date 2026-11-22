"""move notes and rating to books

Revision ID: 0c32af708c7f
Revises: cef1e08c2848
Create Date: 2026-11-22 11:24:17.434039

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0c32af708c7f"
down_revision: str | None = "cef1e08c2848"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("books", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("books", sa.Column("rating", sa.Numeric(2, 1), nullable=True))

    op.execute(
        "UPDATE books SET notes = user_books.notes, rating = user_books.rating "
        "FROM user_books WHERE user_books.book_id = books.id"
    )

    op.drop_column("user_books", "notes")
    op.drop_column("user_books", "rating")


def downgrade() -> None:
    op.add_column("user_books", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("user_books", sa.Column("rating", sa.Numeric(2, 1), nullable=True))

    op.execute(
        "UPDATE user_books SET notes = books.notes, rating = books.rating "
        "FROM books WHERE books.id = user_books.book_id"
    )

    op.drop_column("books", "notes")
    op.drop_column("books", "rating")
