"""drop unique constraint on books isbn

Revision ID: ef1874b394f8
Revises: 1c2fe40b9002
Create Date: 2026-11-22 10:29:00.933054

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ef1874b394f8"
down_revision: str | None = "1c2fe40b9002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONSTRAINT_NAME = "uq_books_isbn"

# Names the unnamed isbn constraint on reflection, which lets batch mode drop it
NAMING_CONVENTION = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def upgrade() -> None:
    with op.batch_alter_table("books", naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint(CONSTRAINT_NAME, type_="unique")


def downgrade() -> None:
    with op.batch_alter_table("books") as batch_op:
        batch_op.create_unique_constraint(CONSTRAINT_NAME, ["isbn"])
