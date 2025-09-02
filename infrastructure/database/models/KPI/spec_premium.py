from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class SpecPremium(Base, TableNameMixin):
    """
    Модель, представляющая сущность показателей премиума специалиста в БД
    """

    __tablename__ = "SpecPremium"

    fullname: Mapped[str] = mapped_column(
        Unicode(250),
        nullable=False,
        name="FULLNAME",
        primary_key=True,
    )
    contacts_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Общее кол-во контактов", name="TC"
    )
    aht: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="AHT специалиста", name="AHT"
    )
    delay: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Задержка специалиста", name="DELAY"
    )
    csi: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="CSI специалиста", name="CSI"
    )
    pok: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Отклик специалиста", name="POK"
    )
    perc_csi: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Процент CSI", name="PERC_CSI"
    )
    gok: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="ГОК специалиста", name="GOK"
    )
    perc_gok: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Процент ГОК", name="PERC_GOK"
    )
    flr: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="FLR специалиста", name="FLR"
    )
    perc_flr: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Процент FLR", name="PERC_FLR"
    )
    perc_discipline: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Процент дисциплины", name="PERC_DISCIPLINE"
    )
    perc_sc: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Процент спец. цели", name="PERC_SC"
    )
    perc_testing: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Процент тестирования", name="PERC_TESTING"
    )
    perc_thanks: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Процент благодарностей", name="PERC_THANKS"
    )
    perc_tutors: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Процент наставничества", name="PERC_TUTORS"
    )
    head_adjust: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Корректировка руководителя", name="HEAD_ADJUST"
    )
    total_premium: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Общая премия", name="TOTAL_PREMIUM"
    )
    sc_one_perc: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Процент выполнения первой спец. цели",
        name="SC_ONE_PERC",
    )
    sc_two_perc: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Процент выполнения второй спец. цели",
        name="SC_TWO_PERC",
    )
    appeals_dw_perc: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Процент КС", name="APPEALS_DW_PERC"
    )
    routing_perc: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Процент переводов",
        name="ROUTING_PERC",
    )
    sales_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Кол-во продаж", name="SalesCount", default=0
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Дата обновления показателей",
        name="UpdateData",
        default=datetime.now,
    )

    def __repr__(self):
        return f"<SpecPremium {self.fullname} {self.total_premium} {self.updated_at}>"
