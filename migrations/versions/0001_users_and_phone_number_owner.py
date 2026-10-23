"""Add users and phone_numbers.owner_id

Revision ID: 0001_users_and_owner
Revises:
Create Date: 2026-10-23
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_users_and_owner"
down_revision = None
branch_labels = None
depends_on = None


# The app also runs Base.metadata.create_all at startup, so each step checks the current schema first.
def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = inspector.get_table_names()

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("api_key_hash", sa.String(length=64), nullable=False),
            sa.Column("api_key", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_users_id", "users", ["id"])
        op.create_index("ix_users_api_key_hash", "users", ["api_key_hash"], unique=True)

    if "phone_numbers" not in tables:
        return
    if "owner_id" in {column["name"] for column in inspector.get_columns("phone_numbers")}:
        return

    number_indexes = {index["name"] for index in inspector.get_indexes("phone_numbers")}
    with op.batch_alter_table("phone_numbers", recreate="auto") as batch:
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_phone_numbers_owner_id_users", "users", ["owner_id"], ["id"])
        if "ix_phone_numbers_number" in number_indexes:
            batch.drop_index("ix_phone_numbers_number")
        batch.create_index("ix_phone_numbers_number", ["number"], unique=False)
        batch.create_index("ix_phone_numbers_owner_id", ["owner_id"])
        batch.create_unique_constraint("uq_phone_numbers_owner_number", ["owner_id", "number"])


def downgrade() -> None:
    with op.batch_alter_table("phone_numbers", recreate="auto") as batch:
        batch.drop_constraint("uq_phone_numbers_owner_number", type_="unique")
        batch.drop_index("ix_phone_numbers_owner_id")
        batch.drop_index("ix_phone_numbers_number")
        batch.create_index("ix_phone_numbers_number", ["number"], unique=True)
        batch.drop_constraint("fk_phone_numbers_owner_id_users", type_="foreignkey")
        batch.drop_column("owner_id")

    op.drop_index("ix_users_api_key_hash", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
