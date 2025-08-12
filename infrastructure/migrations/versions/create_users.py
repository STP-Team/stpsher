"""Create users table

Revision ID: 343bb188ff78
Revises:
Create Date: 2024-02-22 08:49:09.778944

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "343bb188ff78"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id", sa.Integer, autoincrement=True, primary_key=True, nullable=False
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=True, unique=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("fullname", sa.String(length=255), nullable=True),
        sa.Column("division", sa.String(length=255), nullable=True),
        sa.Column("position", sa.String(length=255), nullable=True),
        sa.Column("head", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("role", mysql.TINYINT(), nullable=False, server_default=sa.text("0")),
    )

    # Grant privileges
    op.execute("GRANT DELETE, INSERT, SELECT, UPDATE ON users TO 'stpsher_bot'")


def downgrade() -> None:
    op.drop_table("users")
