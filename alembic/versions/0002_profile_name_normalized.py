"""add unicode-safe profile name lookup

Revision ID: 0002_profile_name_normalized
Revises: 0001_profiles
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_profile_name_normalized"
down_revision = "0001_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("name_normalized", sa.String(length=255), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, name FROM profiles")).mappings()
    for row in rows:
        connection.execute(
            sa.text("UPDATE profiles SET name_normalized = :name_normalized WHERE id = :id"),
            {
                "id": row["id"],
                "name_normalized": str(row["name"]).strip().casefold(),
            },
        )
    with op.batch_alter_table("profiles") as batch_op:
        batch_op.alter_column(
            "name_normalized",
            existing_type=sa.String(length=255),
            nullable=False,
        )
    op.create_index("ix_profiles_name_normalized", "profiles", ["name_normalized"])


def downgrade() -> None:
    op.drop_index("ix_profiles_name_normalized", table_name="profiles")
    with op.batch_alter_table("profiles") as batch_op:
        batch_op.drop_column("name_normalized")
