"""Create purchases table

Revision ID: 71d187cd38e5
Revises: 25f945ec5bae
Create Date: 2025-09-06 12:04:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "71d187cd38e5"
down_revision: Union[str, None] = "25f945ec5bae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "purchases",
        sa.Column(
            "id", sa.Integer, autoincrement=True, primary_key=True, nullable=False
        ),
        sa.Column("user_id", sa.BIGINT, nullable=True),
        sa.Column("product_id", mysql.VARCHAR(255), nullable=False),
        sa.Column("comment", mysql.VARCHAR, nullable=True),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("bought_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("updated_by_user_id", sa.BIGINT, nullable=True),
        sa.Column("status", mysql.VARCHAR(10), nullable=False, server_default=sa.text("'stored'")),
    )

    # Grant privileges
    op.execute("GRANT DELETE, INSERT, SELECT, UPDATE ON purchases TO 'stpsher_bot'")


def downgrade() -> None:
    op.drop_table("purchases")
