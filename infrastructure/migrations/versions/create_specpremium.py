"""Create SpecPremium table

Revision ID: f2d8e7a3b6c9
Revises: b8f3c5a1d4e2
Create Date: 2025-09-06 12:08:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2d8e7a3b6c9"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "SpecPremium",
        sa.Column(
            "FULLNAME",
            sa.Unicode(250),
            primary_key=True,
            nullable=False
        ),
        sa.Column(
            "TC",
            sa.Integer,
            nullable=True,
            comment="Общее кол-во контактов"
        ),
        sa.Column(
            "AHT",
            sa.Integer,
            nullable=True,
            comment="AHT специалиста"
        ),
        sa.Column(
            "DELAY",
            sa.Float,
            nullable=True,
            comment="Задержка специалиста"
        ),
        sa.Column(
            "CSI",
            sa.Float,
            nullable=True,
            comment="CSI специалиста"
        ),
        sa.Column(
            "POK",
            sa.Float,
            nullable=True,
            comment="Отклик специалиста"
        ),
        sa.Column(
            "PERC_CSI",
            sa.Integer,
            nullable=True,
            comment="Процент CSI"
        ),
        sa.Column(
            "GOK",
            sa.Float,
            nullable=True,
            comment="ГОК специалиста"
        ),
        sa.Column(
            "PERC_GOK",
            sa.Integer,
            nullable=True,
            comment="Процент ГОК"
        ),
        sa.Column(
            "FLR",
            sa.Float,
            nullable=True,
            comment="FLR специалиста"
        ),
        sa.Column(
            "PERC_FLR",
            sa.Integer,
            nullable=True,
            comment="Процент FLR"
        ),
        sa.Column(
            "PERC_DISCIPLINE",
            sa.Integer,
            nullable=True,
            comment="Процент дисциплины"
        ),
        sa.Column(
            "PERC_SC",
            sa.Integer,
            nullable=True,
            comment="Процент спец. цели"
        ),
        sa.Column(
            "PERC_TESTING",
            sa.Integer,
            nullable=True,
            comment="Процент тестирования"
        ),
        sa.Column(
            "PERC_THANKS",
            sa.Integer,
            nullable=True,
            comment="Процент благодарностей"
        ),
        sa.Column(
            "PERC_TUTORS",
            sa.Integer,
            nullable=True,
            comment="Процент наставничества"
        ),
        sa.Column(
            "HEAD_ADJUST",
            sa.Integer,
            nullable=True,
            comment="Корректировка руководителя"
        ),
        sa.Column(
            "TOTAL_PREMIUM",
            sa.Integer,
            nullable=True,
            comment="Общая премия"
        ),
        sa.Column(
            "SC_ONE_PERC",
            sa.Float,
            nullable=True,
            comment="Процент выполнения первой спец. цели"
        ),
        sa.Column(
            "SC_TWO_PERC",
            sa.Float,
            nullable=True,
            comment="Процент выполнения второй спец. цели"
        ),
        sa.Column(
            "APPEALS_DW_PERC",
            sa.Float,
            nullable=True,
            comment="Процент КС"
        ),
        sa.Column(
            "ROUTING_PERC",
            sa.Float,
            nullable=True,
            comment="Процент переводов"
        ),
        sa.Column(
            "SalesCount",
            sa.Integer,
            nullable=True,
            comment="Кол-во продаж",
            default=0
        ),
        sa.Column(
            "UpdateData",
            sa.DateTime,
            nullable=True,
            comment="Дата обновления показателей"
        ),
    )

    # Grant privileges
    op.execute("GRANT DELETE, INSERT, SELECT, UPDATE ON SpecPremium TO 'stpsher_bot'")


def downgrade() -> None:
    op.drop_table("SpecPremium")
