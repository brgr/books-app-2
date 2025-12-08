"""seed initial book event types

Revision ID: 5f22316bd406
Revises: 0e6d6f9d7e1d
Create Date: 2025-12-08 16:00:17.827932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f22316bd406'
down_revision: Union[str, None] = '0e6d6f9d7e1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    for code in (
        'added_to_library',
        'started_reading',
        'finished_reading',
    ):
        conn.execute(sa.text("INSERT OR IGNORE INTO book_event_types (code) VALUES (:code)"), {"code": code})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM book_event_types WHERE code IN (:c1, :c2, :c3)"
        ),
        {"c1": 'added_to_library', "c2": 'started_reading', "c3": 'finished_reading'},
    )
