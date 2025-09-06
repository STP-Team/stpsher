"""Create products table

Revision ID: 25f945ec5bae
Revises: e73af0c2a417
Create Date: 2025-09-06 12:03:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "25f945ec5bae"
down_revision: Union[str, None] = "e73af0c2a417"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column(
            "id", sa.Integer, autoincrement=True, primary_key=True, nullable=False
        ),
        sa.Column("name", mysql.VARCHAR(255), nullable=False),
        sa.Column("description", mysql.VARCHAR(255), nullable=False),
        sa.Column("division", mysql.VARCHAR(3), nullable=False),
        sa.Column("cost", sa.Integer, nullable=False),
        sa.Column("count", sa.Integer, nullable=False),
        sa.Column("manager_role", sa.Integer, nullable=False),
    )

    # Grant privileges
    op.execute("GRANT DELETE, INSERT, SELECT, UPDATE ON products TO 'stpsher_bot'")


def downgrade() -> None:
    op.drop_table("products")
