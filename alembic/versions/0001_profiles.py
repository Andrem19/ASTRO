"""create profiles profile_tags chart_cache

Revision ID: 0001_profiles
Revises:
Create Date: 2026-05-13
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_profiles"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("birth_time", sa.Time(), nullable=False),
        sa.Column("birth_place", sa.String(length=512), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("timezone", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_profiles_external_id", "profiles", ["external_id"])

    op.create_table(
        "profile_tags",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("tag", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_profile_tags_profile_id", "profile_tags", ["profile_id"])
    op.create_index("ix_profile_tags_tag", "profile_tags", ["tag"])

    op.create_table(
        "chart_cache",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("settings_hash", sa.String(length=64), nullable=False),
        sa.Column("chart_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("profile_id", "settings_hash", name="uq_chart_cache_profile_settings"),
    )
    op.create_index("ix_chart_cache_profile_id", "chart_cache", ["profile_id"])
    op.create_index("ix_chart_cache_settings_hash", "chart_cache", ["settings_hash"])


def downgrade() -> None:
    op.drop_index("ix_chart_cache_settings_hash", table_name="chart_cache")
    op.drop_index("ix_chart_cache_profile_id", table_name="chart_cache")
    op.drop_table("chart_cache")
    op.drop_index("ix_profile_tags_tag", table_name="profile_tags")
    op.drop_index("ix_profile_tags_profile_id", table_name="profile_tags")
    op.drop_table("profile_tags")
    op.drop_index("ix_profiles_external_id", table_name="profiles")
    op.drop_table("profiles")
