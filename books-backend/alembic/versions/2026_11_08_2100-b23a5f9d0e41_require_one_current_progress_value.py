"""allow at most one current progress value

Revision ID: b23a5f9d0e41
Revises: a12f4e8c9d30
Create Date: 2026-11-08 21:00:00

"""

from collections.abc import Generator, Sequence
from contextlib import contextmanager

from alembic import op

revision: str = "b23a5f9d0e41"
down_revision: str | None = "a12f4e8c9d30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


@contextmanager
def _preserve_sqlite_references() -> Generator[None]:
    connection = op.get_bind()
    context = op.get_context()
    if connection.dialect.name != "sqlite" or context.as_sql:
        yield
        return

    # Rebuilding user_books drops the old table, which would cascade-delete
    # events and shelf placements. PRAGMA changes require no active transaction.
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
        # We arbitrarily chose to retain the page when both values are present.
        op.execute(
            "UPDATE user_books SET current_percent = NULL "
            "WHERE current_page IS NOT NULL AND current_percent IS NOT NULL"
        )
        with op.batch_alter_table("user_books") as batch_op:
            batch_op.create_check_constraint(
                "ck_user_books_at_most_one_progress_value",
                "current_page IS NULL OR current_percent IS NULL",
            )


def downgrade() -> None:
    with (
        _preserve_sqlite_references(),
        op.batch_alter_table("user_books") as batch_op,
    ):
        batch_op.drop_constraint(
            "ck_user_books_at_most_one_progress_value", type_="check"
        )
