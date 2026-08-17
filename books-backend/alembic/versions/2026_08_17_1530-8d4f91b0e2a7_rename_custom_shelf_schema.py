"""rename custom shelf schema

Align the database vocabulary with the ``CustomShelf``, ``CustomShelfPlacement``, and ``ReadingShelf`` model names.
Table renames preserve all existing data and foreign-key relationships.

Revision ID: 8d4f91b0e2a7
Revises: cf19848e976e
Create Date: 2026-08-17 15:30:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8d4f91b0e2a7"
down_revision: Union[str, None] = "cf19848e976e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_postgresql_objects() -> None:
    """Rename PostgreSQL-only schema objects that do not follow table renames."""
    op.execute("ALTER TYPE shelfname RENAME TO reading_shelf")
    op.execute(
        "ALTER TABLE custom_shelves RENAME CONSTRAINT "
        "uq_shelves_user_name TO uq_custom_shelves_user_name"
    )
    op.execute(
        "ALTER TABLE custom_shelf_placements RENAME CONSTRAINT "
        "uq_shelf_items_shelf_user_book "
        "TO uq_custom_shelf_placements_shelf_user_book"
    )
    op.execute(
        "ALTER SEQUENCE IF EXISTS shelves_id_seq RENAME TO custom_shelves_id_seq"
    )
    op.execute(
        "ALTER SEQUENCE IF EXISTS shelf_items_id_seq "
        "RENAME TO custom_shelf_placements_id_seq"
    )


def _restore_postgresql_objects() -> None:
    """Restore PostgreSQL-only object names for downgrade."""
    op.execute("ALTER TYPE reading_shelf RENAME TO shelfname")
    op.execute(
        "ALTER TABLE shelves RENAME CONSTRAINT "
        "uq_custom_shelves_user_name TO uq_shelves_user_name"
    )
    op.execute(
        "ALTER TABLE shelf_items RENAME CONSTRAINT "
        "uq_custom_shelf_placements_shelf_user_book "
        "TO uq_shelf_items_shelf_user_book"
    )
    op.execute(
        "ALTER SEQUENCE IF EXISTS custom_shelves_id_seq RENAME TO shelves_id_seq"
    )
    op.execute(
        "ALTER SEQUENCE IF EXISTS custom_shelf_placements_id_seq "
        "RENAME TO shelf_items_id_seq"
    )


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("shelves", "custom_shelves")
    op.rename_table("shelf_items", "custom_shelf_placements")

    op.drop_index("ix_shelf_items_shelf_sort", table_name="custom_shelf_placements")
    op.create_index(
        "ix_custom_shelf_placements_shelf_sort",
        "custom_shelf_placements",
        ["shelf_id", "sort_order"],
    )

    if op.get_bind().dialect.name == "postgresql":
        _rename_postgresql_objects()


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_custom_shelf_placements_shelf_sort",
        table_name="custom_shelf_placements",
    )
    op.rename_table("custom_shelf_placements", "shelf_items")
    op.rename_table("custom_shelves", "shelves")
    op.create_index(
        "ix_shelf_items_shelf_sort", "shelf_items", ["shelf_id", "sort_order"]
    )

    if op.get_bind().dialect.name == "postgresql":
        _restore_postgresql_objects()
