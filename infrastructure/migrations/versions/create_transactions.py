"""Create transactions table

Revision ID: 97dfd8552155
Revises: 51e2a088905c
Create Date: 2025-09-06 12:06:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "97dfd8552155"
down_revision: Union[str, None] = "51e2a088905c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column(
            "id", sa.BIGINT, autoincrement=True, primary_key=True, nullable=False
        ),
        sa.Column("user_id", sa.BIGINT, nullable=False),
        sa.Column(
            "type",
            sa.Enum("earn", "spend"),
            nullable=False,
            comment="Тип операции: начисление или списание"
        ),
        sa.Column(
            "source_id",
            sa.Integer,
            nullable=True,
            comment="Идентификатор достижения или предмета. Для manual — NULL"
        ),
        sa.Column(
            "source_type",
            sa.Enum("achievement", "product", "manual", "casino"),
            nullable=False,
            comment="Источник транзакции"
        ),
        sa.Column(
            "amount",
            sa.Integer,
            nullable=False,
            comment="Количество баллов"
        ),
        sa.Column(
            "comment",
            sa.String(255),
            nullable=True,
            comment="Комментарий"
        ),
        sa.Column(
            "created_by",
            sa.BIGINT,
            nullable=True,
            comment="ID администратора, создавшего транзакцию"
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            nullable=True,
            default=sa.func.current_timestamp(),
            comment="Дата создания транзакции"
        ),
    )

    # Grant privileges
    op.execute("GRANT DELETE, INSERT, SELECT, UPDATE ON transactions TO 'stpsher_bot'")


def downgrade() -> None:
    op.drop_table("transactions")
