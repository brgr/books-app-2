"""rename status to shelf, store ShelfName enum values in shelves.name

Revision ID: cfe2b6015bf1
Revises: 4f70cb4d4551
Create Date: 2026-07-26 09:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cfe2b6015bf1"
down_revision: Union[str, None] = "4f70cb4d4551"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DISPLAY_TO_ENUM = {
    "To Read": "WANT_TO_READ",
    "Want to Read": "WANT_TO_READ",
    "Currently Reading": "STARTED",
    "Finished": "FINISHED",
    "Abandoned": "ABANDONED",
}

_ENUM_TO_DISPLAY = {
    "WANT_TO_READ": "Want to Read",
    "STARTED": "Currently Reading",
    "FINISHED": "Finished",
    "ABANDONED": "Abandoned",
}


def upgrade() -> None:
    with op.batch_alter_table("user_books") as batch_op:
        batch_op.alter_column(
            "status",
            new_column_name="shelf",
            existing_type=sa.Enum(
                "WANT_TO_READ", "STARTED", "FINISHED", "ABANDONED", name="shelfname"
            ),
        )

    for display, enum_name in _DISPLAY_TO_ENUM.items():
        op.execute(
            sa.text("UPDATE shelves SET name = :enum WHERE name = :display").bindparams(
                enum=enum_name, display=display
            )
        )

    with op.batch_alter_table("shelves") as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.String(100),
            type_=sa.Enum(
                "WANT_TO_READ", "STARTED", "FINISHED", "ABANDONED", name="shelfname"
            ),
        )


def downgrade() -> None:
    with op.batch_alter_table("shelves") as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.Enum(
                "WANT_TO_READ", "STARTED", "FINISHED", "ABANDONED", name="shelfname"
            ),
            type_=sa.String(100),
        )

    for enum_name, display in _ENUM_TO_DISPLAY.items():
        op.execute(
            sa.text("UPDATE shelves SET name = :display WHERE name = :enum").bindparams(
                enum=enum_name, display=display
            )
        )

    op.execute("DELETE FROM shelves WHERE name IN ('Currently Reading', 'Abandoned')")

    with op.batch_alter_table("user_books") as batch_op:
        batch_op.alter_column(
            "shelf",
            new_column_name="status",
            existing_type=sa.Enum(
                "WANT_TO_READ", "STARTED", "FINISHED", "ABANDONED", name="readingstatus"
            ),
        )
