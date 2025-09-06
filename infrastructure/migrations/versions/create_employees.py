"""Create employees table

Revision ID: c1dea76a4e85
Revises: 343bb188ff78
Create Date: 2025-09-06 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1dea76a4e85"
down_revision: Union[str, None] = "343bb188ff78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column(
            "id", sa.BIGINT, primary_key=True, nullable=False
        ),
        sa.Column("user_id", sa.BIGINT, nullable=True),
        sa.Column("username", sa.Unicode, nullable=True),
        sa.Column("division", sa.Unicode, nullable=True),
        sa.Column("position", sa.Unicode, nullable=True),
        sa.Column("fullname", sa.Unicode, nullable=False),
        sa.Column("head", sa.Unicode, nullable=True),
        sa.Column("email", sa.Unicode, nullable=True),
        sa.Column("role", sa.BIGINT, nullable=False),
    )

    # Grant privileges
    op.execute("GRANT DELETE, INSERT, SELECT, UPDATE ON employees TO 'stpsher_bot'")


def downgrade() -> None:
    op.drop_table("employees")
