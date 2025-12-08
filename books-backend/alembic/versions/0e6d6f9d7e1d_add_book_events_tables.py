"""Add book events tables

Revision ID: 0e6d6f9d7e1d
Revises: 1d012f679eaa
Create Date: 2025-03-09 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e6d6f9d7e1d'
down_revision: Union[str, None] = '9876543210ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'book_event_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    op.create_table(
        'book_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_book_id', sa.Integer(), nullable=False),
        sa.Column('event_type_id', sa.Integer(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['event_type_id'], ['book_event_types.id'], ),
        sa.ForeignKeyConstraint(['user_book_id'], ['user_books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_book_events_user_book_id_occurred_at', 'book_events', ['user_book_id', 'occurred_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_book_events_user_book_id_occurred_at', table_name='book_events')
    op.drop_table('book_events')
    op.drop_table('book_event_types')
