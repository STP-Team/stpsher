"""Create RgMonthStats table

Revision ID: b8f3c5a1d4e2
Revises: 97dfd8552155
Create Date: 2025-09-06 12:07:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8f3c5a1d4e2"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "RgMonthStats",
        sa.Column(
            "FULLNAME",
            sa.Unicode(250),
            primary_key=True,
            nullable=False
        ),
        sa.Column(
            "TC",
            sa.Integer,
            nullable=False,
            comment="Общее кол-во контактов"
        ),
        sa.Column(
            "GOK",
            sa.Float,
            nullable=False,
            comment="ГОК группы"
        ),
        sa.Column(
            "AHT",
            sa.Integer,
            nullable=False,
            comment="AHT группы"
        ),
        sa.Column(
            "FLR",
            sa.Float,
            nullable=False,
            comment="FLR группы"
        ),
        sa.Column(
            "CSI",
            sa.Float,
            nullable=False,
            comment="Оценка группы"
        ),
        sa.Column(
            "POK",
            sa.Float,
            nullable=False,
            comment="Отклик группы"
        ),
        sa.Column(
            "DELAY",
            sa.Float,
            nullable=False,
            comment="Задержка группы"
        ),
        sa.Column(
            "SalesCount",
            sa.Integer,
            nullable=False,
            comment="Кол-во продаж группы"
        ),
        sa.Column(
            "UpdateData",
            sa.DateTime,
            nullable=False,
            comment="Дата обновления показателей"
        ),
    )

    # Grant privileges
    op.execute("GRANT DELETE, INSERT, SELECT, UPDATE ON RgMonthStats TO 'stpsher_bot'")


def downgrade() -> None:
    op.drop_table("RgMonthStats")
