from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class HeadPremium(Base, TableNameMixin):
    """
    Модель, представляющая сущность показателей руководителя за месяц в БД
    """

    __tablename__ = "RgPremium"

    fullname: Mapped[str] = mapped_column(
        Unicode(250),
        nullable=False,
        name="FULLNAME",
        primary_key=True,
    )
    contacts_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Общее кол-во контактов", name="TC"
    )

    flr: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="FLR руководителя", name="FLR"
    )
    flr_normative: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Норматив FLR", name="FLR_NORMATIVE"
    )
    flr_normative_rate: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="% выполнения норматива FLR", name="NORM_FLR"
    )
    flr_premium: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="% премии за FLR", name="PERC_FLR"
    )

    gok: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="ГОК руководителя", name="GOK"
    )
    gok_normative: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Норматив ГОК", name="GOK_NORMATIVE"
    )
    gok_normative_rate: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="% выполнения норматива ГОК", name="NORM_GOK"
    )
    gok_premium: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="% премии за ГОК", name="PERC_GOK"
    )

    target: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Спец. цель руководителя", name="PERS_FACT"
    )
    target_type: Mapped[Optional[str]] = mapped_column(
        Unicode(250),
        nullable=True,
        comment="Тип спец. цели руководителя",
        name="PERS_TARGET_TYPE_NAME",
    )
    target_goal_first: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Первый план спец. цели", name="PERS_PLAN_1"
    )
    target_goal_second: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Второй план спец. цели", name="PERS_PLAN_2"
    )
    target_result_first: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="% выполнения первого плана спец. цели",
        name="PERS_RESULT_1",
    )
    target_result_second: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="% выполнения вторго плана спец. цели",
        name="PERS_RESULT_2",
    )
    target_premium: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="% премии за спец. цель", name="PERS_PERCENT"
    )
    pers_target_manual: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Ручное выставление спец. цели",
        name="PERS_TARGET_MANUAL",
    )

    sales_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Реальные продажи", name="SalesCount"
    )
    sales_potential: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Потенциальные продажи", name="SalesPotential"
    )

    head_adjust: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Корректировка руководителя", name="HEAD_ADJUST"
    )
    total_premium: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Общая премия", name="TOTAL_PREMIUM"
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        name="UpdateData",
        default=datetime.now,
    )

    def __repr__(self):
        return f"<HeadPremium {self.fullname} {self.contacts_count} {self.gok} {self.flr} {self.sales_count} {self.total_premium} {self.updated_at}>"
