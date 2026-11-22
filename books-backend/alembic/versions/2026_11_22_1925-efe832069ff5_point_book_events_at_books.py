"""point book events at books

Revision ID: efe832069ff5
Revises: 85090ab0a392
Create Date: 2026-11-22 19:25:42.503133

"""

from collections.abc import Generator, Sequence
from contextlib import contextmanager

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "efe832069ff5"
down_revision: str | None = "85090ab0a392"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


@contextmanager
def _preserve_sqlite_references() -> Generator[None]:
    connection = op.get_bind()
    context = op.get_context()
    if connection.dialect.name != "sqlite" or context.as_sql:
        yield
        return

    # Rebuilding book_events drops the old table, which would cascade-delete the
    # notes, ratings, progress and other details stored for each event. PRAGMA
    # changes require no active transaction.
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
        with op.batch_alter_table("book_events") as batch_op:
            batch_op.add_column(sa.Column("book_id", sa.Integer(), nullable=True))

        op.execute(
            "UPDATE book_events SET book_id = user_books.book_id "
            "FROM user_books WHERE user_books.id = book_events.user_book_id"
        )

        with op.batch_alter_table("book_events") as batch_op:
            batch_op.drop_index("ix_book_events_user_book_id_occurred_at")
            batch_op.drop_column("user_book_id")
            batch_op.alter_column("book_id", existing_type=sa.Integer(), nullable=False)
            batch_op.create_foreign_key(
                "fk_book_events_book_id_books",
                "books",
                ["book_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.create_index(
                "ix_book_events_book_id_occurred_at", ["book_id", "occurred_at"]
            )


def downgrade() -> None:
    with _preserve_sqlite_references():
        with op.batch_alter_table("book_events") as batch_op:
            batch_op.add_column(sa.Column("user_book_id", sa.Integer(), nullable=True))

        op.execute(
            "UPDATE book_events SET user_book_id = user_books.id "
            "FROM user_books WHERE user_books.book_id = book_events.book_id"
        )

        with op.batch_alter_table("book_events") as batch_op:
            batch_op.drop_index("ix_book_events_book_id_occurred_at")
            batch_op.drop_column("book_id")
            batch_op.alter_column(
                "user_book_id", existing_type=sa.Integer(), nullable=False
            )
            batch_op.create_foreign_key(
                "fk_book_events_user_book_id_user_books",
                "user_books",
                ["user_book_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.create_index(
                "ix_book_events_user_book_id_occurred_at",
                ["user_book_id", "occurred_at"],
            )
