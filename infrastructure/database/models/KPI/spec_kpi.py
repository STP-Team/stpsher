from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class SpecDayKPI(Base, TableNameMixin):
    """
    Модель, представляющая сущность показателей специалиста за день в БД
    """

    __tablename__ = "KpiDay"

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
    flr: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="FLR специалиста", name="FLR"
    )
    csi: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="OK специалиста", name="CSI"
    )
    pok: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Отклик специалиста", name="POK"
    )
    delay: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Задержка специалиста", name="DELAY"
    )
    sales_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Кол-во продаж специалиста", name="SalesCount"
    )
    sales_potential: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Кол-во потенциальных продаж специалиста",
        name="SalesPotential",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Дата обновления показателей",
        name="UpdateData",
        default=datetime.now,
    )
    kpi_extract_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Начальная дата выгружаемых показателей",
        name="KpiExtractDate",
    )

    def __repr__(self):
        return f"<SpecDayKPI {self.fullname} {self.contacts_count}>"


class SpecWeekKPI(Base, TableNameMixin):
    """
    Модель, представляющая сущность показателей специалиста за неделю в БД
    """

    __tablename__ = "KpiWeek"

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
    flr: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="FLR специалиста", name="FLR"
    )
    csi: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="OK специалиста", name="CSI"
    )
    pok: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Отклик специалиста", name="POK"
    )
    delay: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Задержка специалиста", name="DELAY"
    )
    sales_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Кол-во продаж специалиста", name="SalesCount"
    )
    sales_potential: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Кол-во потенциальных продаж специалиста",
        name="SalesPotential",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Дата обновления показателей",
        name="UpdateData",
        default=datetime.now,
    )
    kpi_extract_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Начальная дата выгружаемых показателей",
        name="KpiExtractDate",
    )

    def __repr__(self):
        return f"<SpecWeekKPI {self.fullname} {self.contacts_count}>"


class SpecMonthKPI(Base, TableNameMixin):
    """
    Модель, представляющая сущность показателей специалиста за месяц в БД
    """

    __tablename__ = "KpiMonth"

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
    flr: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="FLR специалиста", name="FLR"
    )
    csi: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="OK специалиста", name="CSI"
    )
    pok: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Отклик специалиста", name="POK"
    )
    delay: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Задержка специалиста", name="DELAY"
    )
    sales_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Кол-во продаж специалиста",
        name="SalesCount",
        default=0,
    )
    sales_potential: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Кол-во потенциальных продаж специалиста",
        name="SalesPotential",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Дата обновления показателей",
        name="UpdateData",
        default=datetime.now,
    )
    kpi_extract_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Начальная дата выгружаемых показателей",
        name="KpiExtractDate",
    )

    def __repr__(self):
        return f"<SpecMonthKPI {self.fullname} {self.contacts_count}>"
