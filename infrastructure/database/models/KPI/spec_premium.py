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
    delay: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Задержка специалиста", name="DELAY"
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

    csi: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Оценка специалиста", name="CSI"
    )
    csi_normative: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Норматив оценки", name="CSI_NORMATIVE"
    )
    csi_normative_rate: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="% выполнения норматива оценки", name="NORM_CSI"
    )
    csi_premium: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="% премии за оценку", name="PERC_CSI"
    )

    csi_response: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Отклик", name="CSI_RESPONSE"
    )
    csi_response_normative: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Норматив отклика", name="CSI_RESPONSE_NORMATIVE"
    )
    csi_response_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="% выполнения норматива отклика",
        name="NORM_CSI_RESPONSE",
    )

    flr: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="FLR специалиста", name="FLR"
    )
    flr_normative: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Норматив FLR", name="FLR_NORMATIVE"
    )
    flr_normative_rate: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="% выполнения норматива FLR", name="NORM_FLR"
    )
    flr_premium: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="% премии за FLR", name="PERC_FLR"
    )

    gok: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="ГОК специалиста", name="GOK"
    )
    gok_normative: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Норматив ГОК", name="GOK_NORMATIVE"
    )
    gok_normative_rate: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="% выполнения норматива ГОК", name="NORM_GOK"
    )
    gok_premium: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="% премии за ГОК", name="PERC_GOK"
    )

    target: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Спец. цель специалиста", name="PERS_FACT"
    )
    target_type: Mapped[str | None] = mapped_column(
        Unicode(250),
        nullable=True,
        comment="Тип спец. цели специалиста",
        name="PERS_TARGET_TYPE_NAME",
    )
    target_goal_first: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Первый план спец. цели", name="PERS_PLAN_1"
    )
    target_goal_second: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Второй план спец. цели", name="PERS_PLAN_2"
    )
    target_result_first: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="% выполнения первого плана спец. цели",
        name="PERS_RESULT_1",
    )
    target_result_second: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="% выполнения второго плана спец. цели",
        name="PERS_RESULT_2",
    )
    target_premium: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="% премии за спец. цель", name="PERS_PERCENT"
    )
    pers_target_manual: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Ручное выставление спец. цели",
        name="PERS_TARGET_MANUAL",
    )

    discipline_premium: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Процент дисциплины", name="PERC_DISCIPLINE"
    )
    tests_premium: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Процент тестирования", name="PERC_TESTING"
    )
    thanks_premium: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Процент благодарностей", name="PERC_THANKS"
    )
    tutors_premium: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Процент наставничества", name="PERC_TUTORS"
    )

    head_adjust_premium: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Корректировка руководителя", name="HEAD_ADJUST"
    )
    total_premium: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Общая премия", name="TOTAL_PREMIUM"
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
