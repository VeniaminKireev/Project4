"""init

Revision ID: 20260310_0001
Revises:
Create Date: 2026-03-10 00:00:00
"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20260310_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("short_code", sa.String(length=32), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("click_count", sa.Integer(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_links_id"), "links", ["id"], unique=False)
    op.create_index(op.f("ix_links_short_code"), "links", ["short_code"], unique=True)
    op.create_index("ix_links_original_url", "links", ["original_url"], unique=False)
    op.create_index("ix_links_expires_at", "links", ["expires_at"], unique=False)

    op.create_table(
        "expired_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("short_code", sa.String(length=32), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expired_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("click_count", sa.Integer(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_expired_links_id"), "expired_links", ["id"], unique=False)
    op.create_index(op.f("ix_expired_links_short_code"), "expired_links", ["short_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_expired_links_short_code"), table_name="expired_links")
    op.drop_index(op.f("ix_expired_links_id"), table_name="expired_links")
    op.drop_table("expired_links")

    op.drop_index("ix_links_expires_at", table_name="links")
    op.drop_index("ix_links_original_url", table_name="links")
    op.drop_index(op.f("ix_links_short_code"), table_name="links")
    op.drop_index(op.f("ix_links_id"), table_name="links")
    op.drop_table("links")

    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
