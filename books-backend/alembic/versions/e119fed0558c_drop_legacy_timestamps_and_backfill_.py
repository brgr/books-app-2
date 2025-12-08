"""drop legacy timestamps and backfill events

Revision ID: e119fed0558c
Revises: 5f22316bd406
Create Date: 2025-12-08 16:41:34.436659

"""
from datetime import UTC, datetime
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e119fed0558c'
down_revision: Union[str, None] = '5f22316bd406'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Ensure event types exist (idempotent safety)
    for code in ('added_to_library', 'started_reading', 'finished_reading'):
        conn.execute(
            sa.text("INSERT OR IGNORE INTO book_event_types (code) VALUES (:code)"),
            {"code": code},
        )

    user_books = conn.execute(
        sa.text(
            "SELECT id, user_id, book_id, status, started_at, finished_at, created_at "
            "FROM user_books"
        )
    ).mappings()

    for row in user_books:
        user_book_id = row["id"]
        created_at = row["created_at"] or datetime.now(UTC)
        started_at = row["started_at"]
        finished_at = row["finished_at"]

        add_exists = conn.execute(
            sa.text(
                "SELECT 1 FROM book_events be "
                "JOIN book_event_types bet ON be.event_type_id = bet.id "
                "WHERE be.user_book_id = :user_book_id AND bet.code = 'added_to_library' "
                "LIMIT 1"
            ),
            {"user_book_id": user_book_id},
        ).scalar()

        if not add_exists:
            conn.execute(
                sa.text(
                    "INSERT INTO book_events (id, user_book_id, event_type_id, occurred_at) "
                    "VALUES (:id, :user_book_id, "
                    "(SELECT id FROM book_event_types WHERE code = 'added_to_library'), "
                    ":occurred_at)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "user_book_id": user_book_id,
                    "occurred_at": created_at,
                },
            )

        if started_at:
            start_exists = conn.execute(
                sa.text(
                    "SELECT 1 FROM book_events be "
                    "JOIN book_event_types bet ON be.event_type_id = bet.id "
                    "WHERE be.user_book_id = :user_book_id AND bet.code = 'started_reading' "
                    "LIMIT 1"
                ),
                {"user_book_id": user_book_id},
            ).scalar()

            if not start_exists:
                conn.execute(
                    sa.text(
                        "INSERT INTO book_events (id, user_book_id, event_type_id, occurred_at) "
                        "VALUES (:id, :user_book_id, "
                        "(SELECT id FROM book_event_types WHERE code = 'started_reading'), "
                        ":occurred_at)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "user_book_id": user_book_id,
                        "occurred_at": started_at,
                    },
                )

        if finished_at:
            # Ensure a start exists to maintain ordering for historic data
            start_exists = conn.execute(
                sa.text(
                    "SELECT 1 FROM book_events be "
                    "JOIN book_event_types bet ON be.event_type_id = bet.id "
                    "WHERE be.user_book_id = :user_book_id AND bet.code = 'started_reading' "
                    "LIMIT 1"
                ),
                {"user_book_id": user_book_id},
            ).scalar()
            if not start_exists:
                conn.execute(
                    sa.text(
                        "INSERT INTO book_events (id, user_book_id, event_type_id, occurred_at) "
                        "VALUES (:id, :user_book_id, "
                        "(SELECT id FROM book_event_types WHERE code = 'started_reading'), "
                        ":occurred_at)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "user_book_id": user_book_id,
                        "occurred_at": finished_at,
                    },
                )

            finish_exists = conn.execute(
                sa.text(
                    "SELECT 1 FROM book_events be "
                    "JOIN book_event_types bet ON be.event_type_id = bet.id "
                    "WHERE be.user_book_id = :user_book_id AND bet.code = 'finished_reading' "
                    "LIMIT 1"
                ),
                {"user_book_id": user_book_id},
            ).scalar()

            if not finish_exists:
                conn.execute(
                    sa.text(
                        "INSERT INTO book_events (id, user_book_id, event_type_id, occurred_at) "
                        "VALUES (:id, :user_book_id, "
                        "(SELECT id FROM book_event_types WHERE code = 'finished_reading'), "
                        ":occurred_at)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "user_book_id": user_book_id,
                        "occurred_at": finished_at,
                    },
                )

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('created_at')

    with op.batch_alter_table('books') as batch_op:
        batch_op.drop_column('created_at')
        batch_op.drop_column('updated_at')

    with op.batch_alter_table('user_books') as batch_op:
        batch_op.drop_column('created_at')
        batch_op.drop_column('updated_at')


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('books') as batch_op:
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('user_books') as batch_op:
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))
