"""Create KpiMonth table

Revision ID: e6b9d4a7f1c2
Revises: c3f7a2d5e8b4
Create Date: 2025-09-06 12:11:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6b9d4a7f1c2"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "KpiMonth",
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
            "FLR",
            sa.Float,
            nullable=True,
            comment="FLR специалиста"
        ),
        sa.Column(
            "CSI",
            sa.Float,
            nullable=True,
            comment="OK специалиста"
        ),
        sa.Column(
            "POK",
            sa.Float,
            nullable=True,
            comment="Отклик специалиста"
        ),
        sa.Column(
            "DELAY",
            sa.Float,
            nullable=True,
            comment="Задержка специалиста"
        ),
        sa.Column(
            "SalesCount",
            sa.Integer,
            nullable=True,
            comment="Кол-во продаж специалиста",
            default=0
        ),
        sa.Column(
            "SalesPotential",
            sa.Integer,
            nullable=True,
            comment="Кол-во потенциальных продаж специалиста"
        ),
        sa.Column(
            "UpdateData",
            sa.DateTime,
            nullable=True,
            comment="Дата обновления показателей"
        ),
    )

    # Grant privileges
    op.execute("GRANT DELETE, INSERT, SELECT, UPDATE ON KpiMonth TO 'stpsher_bot'")


def downgrade() -> None:
    op.drop_table("KpiMonth")
