"""point shelf placements at books

Revision ID: db180c6e3e54
Revises: efe832069ff5
Create Date: 2026-11-22 20:56:29.216959

"""

from collections.abc import Generator, Sequence
from contextlib import contextmanager

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "db180c6e3e54"
down_revision: str | None = "efe832069ff5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


@contextmanager
def _preserve_sqlite_references() -> Generator[None]:
    connection = op.get_bind()
    context = op.get_context()
    if connection.dialect.name != "sqlite" or context.as_sql:
        yield
        return

    # Turns foreign keys off for the rebuild of shelf_placements, as SQLite's
    # steps for altering a table require. PRAGMA changes require no active
    # transaction.
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
        with op.batch_alter_table("shelf_placements") as batch_op:
            batch_op.add_column(sa.Column("book_id", sa.Integer(), nullable=True))

        op.execute(
            "UPDATE shelf_placements SET book_id = user_books.book_id "
            "FROM user_books WHERE user_books.id = shelf_placements.user_book_id"
        )

        with op.batch_alter_table("shelf_placements") as batch_op:
            batch_op.drop_constraint(
                "uq_shelf_placements_shelf_user_book", type_="unique"
            )
            batch_op.drop_column("user_book_id")
            batch_op.alter_column("book_id", existing_type=sa.Integer(), nullable=False)
            batch_op.create_foreign_key(
                "fk_shelf_placements_book_id_books",
                "books",
                ["book_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.create_unique_constraint(
                "uq_shelf_placements_shelf_book", ["shelf_id", "book_id"]
            )


def downgrade() -> None:
    with _preserve_sqlite_references():
        with op.batch_alter_table("shelf_placements") as batch_op:
            batch_op.add_column(sa.Column("user_book_id", sa.Integer(), nullable=True))

        op.execute(
            "UPDATE shelf_placements SET user_book_id = user_books.id "
            "FROM user_books WHERE user_books.book_id = shelf_placements.book_id"
        )

        with op.batch_alter_table("shelf_placements") as batch_op:
            batch_op.drop_constraint("uq_shelf_placements_shelf_book", type_="unique")
            batch_op.drop_column("book_id")
            batch_op.alter_column(
                "user_book_id", existing_type=sa.Integer(), nullable=False
            )
            batch_op.create_foreign_key(
                "fk_shelf_placements_user_book_id_user_books",
                "user_books",
                ["user_book_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.create_unique_constraint(
                "uq_shelf_placements_shelf_user_book", ["shelf_id", "user_book_id"]
            )
