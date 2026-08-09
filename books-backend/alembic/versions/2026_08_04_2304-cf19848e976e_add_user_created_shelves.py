"""add user created shelves

``shelves`` becomes the table of user-created shelves. It previously held one
row per built-in shelf per user, purely to hand them stable ids; the API
addresses built-in shelves by name instead, so those rows are dead weight and
are dropped. The column shape is unchanged, so this is a delete, not a rebuild.

``shelf_items`` returns (it was dropped in 4f70cb4d4551). It went because
built-in shelf membership is derived and needs no storage -- which is still
true, and those shelves still do not use this table. Custom shelves are the
opposite: membership is assigned, a book can be on many of them, and each
placement carries its own position. That genuinely needs rows.

Revision ID: cf19848e976e
Revises: 020b4223eeb8
Create Date: 2026-08-04 23:04:53.622005

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cf19848e976e"
down_revision: Union[str, None] = "020b4223eeb8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Built-in shelf rows. Nothing referenced them once the API switched to
    # addressing built-in shelves by name, and shelf_items does not exist yet,
    # so there is nothing to cascade to.
    op.execute("DELETE FROM shelves")

    with op.batch_alter_table("shelves") as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.Enum(
                "WANT_TO_READ", "STARTED", "FINISHED", "ABANDONED", name="shelfname"
            ),
            type_=sa.String(100),
            existing_nullable=False,
        )

    op.create_table(
        "shelf_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "shelf_id",
            sa.Integer(),
            sa.ForeignKey("shelves.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_book_id",
            sa.Integer(),
            sa.ForeignKey("user_books.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Numeric(20, 10), nullable=False),
        sa.UniqueConstraint(
            "shelf_id", "user_book_id", name="uq_shelf_items_shelf_user_book"
        ),
    )
    op.create_index(
        "ix_shelf_items_shelf_sort", "shelf_items", ["shelf_id", "sort_order"]
    )


def downgrade() -> None:
    """Downgrade schema.

    User-created shelves have no other source, so they are lost rather than
    reconstructed; the built-in rows this deletes are re-derivable and are put
    back. ``shelves.name`` held the ShelfName member NAME (WANT_TO_READ), as
    SQLAlchemy's Enum type stores members by name.
    """
    op.drop_index("ix_shelf_items_shelf_sort", table_name="shelf_items")
    op.drop_table("shelf_items")

    op.execute("DELETE FROM shelves")
    with op.batch_alter_table("shelves") as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.String(100),
            type_=sa.Enum(
                "WANT_TO_READ", "STARTED", "FINISHED", "ABANDONED", name="shelfname"
            ),
            existing_nullable=False,
        )
    op.execute(
        "INSERT INTO shelves (user_id, name) "
        "SELECT u.id, n.name FROM users u CROSS JOIN ("
        "  SELECT 'WANT_TO_READ' AS name UNION ALL SELECT 'STARTED' "
        "  UNION ALL SELECT 'FINISHED' UNION ALL SELECT 'ABANDONED'"
        ") n"
    )
