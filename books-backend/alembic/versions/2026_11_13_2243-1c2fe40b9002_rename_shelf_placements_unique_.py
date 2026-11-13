"""rename shelf placements unique constraint

Revision ID: 1c2fe40b9002
Revises: b23a5f9d0e41
Create Date: 2026-11-13 22:43:21.807239

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1c2fe40b9002"
down_revision: str | None = "b23a5f9d0e41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD_NAME = "uq_shelf_items_shelf_user_book"
NEW_NAME = "uq_shelf_placements_shelf_user_book"
COLUMNS = ["shelf_id", "user_book_id"]


# The constraint kept the name from when the table was called shelf_items.
# No table references shelf_placements, so rebuilding it cascades nothing.
def upgrade() -> None:
    with op.batch_alter_table("shelf_placements") as batch_op:
        batch_op.drop_constraint(OLD_NAME, type_="unique")
        batch_op.create_unique_constraint(NEW_NAME, COLUMNS)


def downgrade() -> None:
    with op.batch_alter_table("shelf_placements") as batch_op:
        batch_op.drop_constraint(NEW_NAME, type_="unique")
        batch_op.create_unique_constraint(OLD_NAME, COLUMNS)
