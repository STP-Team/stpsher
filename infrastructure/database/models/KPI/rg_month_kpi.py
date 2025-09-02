from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class HeadMonthKPI(Base, TableNameMixin):
    """
    Модель, представляющая сущность показателей руководителя за месяц в БД
    """

    __tablename__ = "RgMonthStats"

    fullname: Mapped[str] = mapped_column(
        Unicode(250),
        nullable=False,
        name="FULLNAME",
        primary_key=True,
    )
    contacts_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Общее кол-во контактов", name="TC"
    )
    gok: Mapped[float] = mapped_column(
        Float, nullable=False, comment="ГОК группы", name="GOK"
    )
    aht: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="AHT группы", name="AHT"
    )
    flr: Mapped[float] = mapped_column(
        Float, nullable=False, comment="FLR группы", name="FLR"
    )
    csi: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Оценка группы", name="CSI"
    )
    pok: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Отклик группы", name="POK"
    )
    delay: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Задержка группы", name="DELAY"
    )
    sales_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Кол-во продаж группы", name="SalesCount"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Дата обновления показателей",
        name="UpdateData",
        default=datetime.now,
    )

    def __repr__(self):
        return f"<HeadMonthKPI {self.fullname} {self.contacts_count} {self.gok} {self.aht} {self.flr} {self.csi} {self.pok} {self.delay} {self.sales_count} {self.updated_at}>"
