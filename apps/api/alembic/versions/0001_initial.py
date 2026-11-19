"""Initial schema: users, lab_sessions, lab_progress, grades, node_images.

Revision ID: 0001
Revises:
Create Date: 2026-11-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), server_default=""),
        sa.Column("provider", sa.String(32), server_default="local"),
        sa.Column("provider_id", sa.String(255), server_default=""),
        sa.Column("role", sa.String(32), server_default="student"),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "lab_sessions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("lab_slug", sa.String(128), nullable=False),
        sa.Column("clab_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), server_default="queued"),
        sa.Column("cpu_limit", sa.Float(), server_default="4.0"),
        sa.Column("memory_limit_mb", sa.Integer(), server_default="4096"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "lab_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("lab_slug", sa.String(128), nullable=False),
        sa.Column("objective_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), server_default="pending"),
        sa.Column("detail", sa.Text(), server_default=""),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "grades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("lab_slug", sa.String(128), nullable=False),
        sa.Column("session_id", sa.String(32), nullable=False),
        sa.Column("score", sa.Integer(), server_default="0"),
        sa.Column("total", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "node_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("vendor", sa.String(64), nullable=False),
        sa.Column("image_ref", sa.String(255), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), server_default="0"),
        sa.Column("uploaded_by", sa.String(255), server_default=""),
        sa.Column("license_acknowledged", sa.Boolean(), server_default="0"),
        sa.Column("loaded", sa.Boolean(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("node_images")
    op.drop_table("grades")
    op.drop_table("lab_progress")
    op.drop_table("lab_sessions")
    op.drop_table("users")
