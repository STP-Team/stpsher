"""Create schedules table

Revision ID: 51e2a088905c
Revises: 71d187cd38e5
Create Date: 2025-09-06 12:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "51e2a088905c"
down_revision: Union[str, None] = "71d187cd38e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedules",
        sa.Column(
            "id", sa.Integer, autoincrement=True, primary_key=True, nullable=False
        ),
        sa.Column(
            "file_id",
            sa.Text,
            nullable=False,
            comment="Идентификатор Telegram загруженного файла"
        ),
        sa.Column(
            "file_name",
            sa.String(255),
            nullable=True,
            comment="Название загруженного файла"
        ),
        sa.Column(
            "file_size",
            sa.BIGINT,
            nullable=True,
            comment="Размер файла в байтах"
        ),
        sa.Column("uploaded_by_user_id", sa.BIGINT, nullable=False),
        sa.Column(
            "uploaded_at",
            sa.TIMESTAMP,
            nullable=False,
            server_default=sa.func.current_timestamp()
        ),
    )

    # Grant privileges
    op.execute("GRANT DELETE, INSERT, SELECT, UPDATE ON schedules TO 'stpsher_bot'")


def downgrade() -> None:
    op.drop_table("schedules")
