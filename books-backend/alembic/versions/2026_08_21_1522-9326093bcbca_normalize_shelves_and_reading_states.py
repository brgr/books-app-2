"""normalize shelves and reading states

Revision ID: 9326093bcbca
Revises: 8d4f91b0e2a7
Create Date: 2026-08-21 15:22:17.932233

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9326093bcbca"
down_revision: str | None = "8d4f91b0e2a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("custom_shelves", "shelves")
    op.rename_table("custom_shelf_placements", "shelf_placements")
    op.drop_index(
        "ix_custom_shelf_placements_shelf_sort", table_name="shelf_placements"
    )
    op.create_index(
        "ix_shelf_placements_shelf_sort", "shelf_placements", ["shelf_id", "sort_order"]
    )

    with op.batch_alter_table("shelves") as batch:
        batch.add_column(sa.Column("kind", sa.String(20), nullable=True))
        batch.drop_constraint(
            "uq_custom_shelves_user_name"
            if op.get_bind().dialect.name == "postgresql"
            else "uq_shelves_user_name",
            type_="unique",
        )
        batch.create_unique_constraint(
            "uq_shelves_user_kind_name", ["user_id", "kind", "name"]
        )

    op.execute("UPDATE shelves SET kind = 'CUSTOM'")
    with op.batch_alter_table("shelves") as batch:
        batch.alter_column("kind", nullable=False)

    # One system-owned reading shelf per state and user. Existing membership
    # and ordering become ordinary shelf placements.
    for name in ("want_to_read", "started", "paused", "finished", "abandoned"):
        op.execute(
            "INSERT INTO shelves (user_id, kind, name) "
            f"SELECT id, 'READING', '{name}' FROM users"
        )
    op.execute(
        """
        INSERT INTO shelf_placements (shelf_id, user_book_id, sort_order)
        SELECT s.id, ub.id, COALESCE(ub.sort_order, ub.id * 1000)
        FROM user_books ub
        JOIN shelves s ON s.user_id = ub.user_id AND s.kind = 'READING'
          AND s.name = CASE ub.reading_shelf
            WHEN 'WANT_TO_READ' THEN 'want_to_read'
            WHEN 'STARTED' THEN 'started'
            WHEN 'FINISHED' THEN 'finished'
            WHEN 'ABANDONED' THEN 'abandoned'
          END
        """
    )
    with op.batch_alter_table("user_books") as batch:
        batch.drop_column("reading_shelf")
        batch.drop_column("sort_order")

    op.bulk_insert(
        sa.table("book_event_types", sa.column("code", sa.String)),
        [
            {"code": "paused_reading"},
            {"code": "resumed_reading"},
            {"code": "abandoned_reading"},
        ],
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrading normalized shelves would discard reading placements"
    )
