"""move reading progress to books

Revision ID: 85090ab0a392
Revises: 0c32af708c7f
Create Date: 2026-11-22 19:10:00.414300

"""

from collections.abc import Generator, Sequence
from contextlib import contextmanager

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "85090ab0a392"
down_revision: str | None = "0c32af708c7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PROGRESS_CHECK = "current_page IS NULL OR current_percent IS NULL"
BOOKS_CHECK_NAME = "ck_books_at_most_one_progress_value"
USER_BOOKS_CHECK_NAME = "ck_user_books_at_most_one_progress_value"


@contextmanager
def _preserve_sqlite_references() -> Generator[None]:
    connection = op.get_bind()
    context = op.get_context()
    if connection.dialect.name != "sqlite" or context.as_sql:
        yield
        return

    # Rebuilding user_books drops the old table, which would cascade-delete
    # events and shelf placements. Rebuilding books would fail on the foreign
    # key from user_books. PRAGMA changes require no active transaction.
    with context.autocommit_block():
        foreign_keys_enabled = bool(
            connection.exec_driver_sql("PRAGMA foreign_keys").scalar()
        )
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")

    try:
        # A savepoint also makes DDL transactional under SQLite's legacy
        # transaction control, so failures roll back the rebuild.
        with connection.begin_nested():
            yield
    finally:
        with context.autocommit_block():
            connection.exec_driver_sql(
                "PRAGMA foreign_keys=ON"
                if foreign_keys_enabled
                else "PRAGMA foreign_keys=OFF"
            )


def upgrade() -> None:
    with _preserve_sqlite_references():
        with op.batch_alter_table("books") as batch_op:
            batch_op.add_column(sa.Column("current_page", sa.Integer(), nullable=True))
            batch_op.add_column(
                sa.Column("current_percent", sa.Numeric(5, 2), nullable=True)
            )
            batch_op.create_check_constraint(BOOKS_CHECK_NAME, PROGRESS_CHECK)

        op.execute(
            "UPDATE books SET current_page = user_books.current_page, "
            "current_percent = user_books.current_percent "
            "FROM user_books WHERE user_books.book_id = books.id"
        )

        with op.batch_alter_table("user_books") as batch_op:
            batch_op.drop_constraint(USER_BOOKS_CHECK_NAME, type_="check")
            batch_op.drop_column("current_page")
            batch_op.drop_column("current_percent")


def downgrade() -> None:
    with _preserve_sqlite_references():
        with op.batch_alter_table("user_books") as batch_op:
            batch_op.add_column(sa.Column("current_page", sa.Integer(), nullable=True))
            batch_op.add_column(
                sa.Column("current_percent", sa.Numeric(5, 2), nullable=True)
            )
            batch_op.create_check_constraint(USER_BOOKS_CHECK_NAME, PROGRESS_CHECK)

        op.execute(
            "UPDATE user_books SET current_page = books.current_page, "
            "current_percent = books.current_percent "
            "FROM books WHERE books.id = user_books.book_id"
        )

        with op.batch_alter_table("books") as batch_op:
            batch_op.drop_constraint(BOOKS_CHECK_NAME, type_="check")
            batch_op.drop_column("current_page")
            batch_op.drop_column("current_percent")
