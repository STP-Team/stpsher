"""Create achievements table

Revision ID: aa9682cc8628
Revises: c1dea76a4e85
Create Date: 2025-09-06 12:01:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "aa9682cc8628"
down_revision: Union[str, None] = "c1dea76a4e85"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "achievements",
        sa.Column(
            "id", sa.Integer, autoincrement=True, primary_key=True, nullable=False
        ),
        sa.Column("name", mysql.VARCHAR(30), nullable=False),
        sa.Column("description", mysql.VARCHAR(255), nullable=False),
        sa.Column("division", mysql.VARCHAR(3), nullable=False),
        sa.Column("kpi", mysql.VARCHAR(3), nullable=False),
        sa.Column("reward", sa.Integer, nullable=False),
        sa.Column("position", mysql.VARCHAR(31), nullable=False),
        sa.Column("period", mysql.VARCHAR(1), nullable=False),
    )

    # Grant privileges
    op.execute("GRANT DELETE, INSERT, SELECT, UPDATE ON achievements TO 'stpsher_bot'")


def downgrade() -> None:
    op.drop_table("achievements")
