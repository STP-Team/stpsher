"""Create broadcasts table

Revision ID: e73af0c2a417
Revises: aa9682cc8628
Create Date: 2025-09-06 12:02:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e73af0c2a417"
down_revision: Union[str, None] = "aa9682cc8628"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "broadcasts",
        sa.Column(
            "id", sa.Integer, autoincrement=True, primary_key=True, nullable=False
        ),
        sa.Column(
            "user_id",
            sa.BIGINT,
            nullable=False,
            comment="Идентификатор владельца рассылки",
        ),
        sa.Column(
            "type",
            sa.Enum("division", "group"),
            nullable=False,
            comment="Тип рассылки: division или group",
        ),
        sa.Column(
            "target",
            sa.String(255),
            nullable=False,
            comment="Конкретная цель рассылки: подразделение (НЦК, НТП1, НТП2) или выбранная группа",
        ),
        sa.Column("text", sa.Text, nullable=False, comment="Текст рассылки"),
        sa.Column(
            "recipients",
            sa.JSON,
            nullable=True,
            comment="Список user_id, получивших рассылку",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )

    # Grant privileges
    op.execute("GRANT DELETE, INSERT, SELECT, UPDATE ON broadcasts TO 'stpsher_bot'")


def downgrade() -> None:
    op.drop_table("broadcasts")
