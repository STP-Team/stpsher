import datetime
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from stp_database import Employee

from infrastructure.api.production_calendar import production_calendar
from tgbot.misc.dicts import russian_months
from tgbot.services.files_processing.core.analyzers import ScheduleAnalyzer
from tgbot.services.files_processing.parsers.schedule import ScheduleParser

from .pay_rates import PayRateService

schedule_parser = ScheduleParser()


@dataclass
class SalaryCalculationResult:
    """Модель результата вычислений зарплаты.

    Содержит все данные о расчете зарплаты сотрудника за месяц,
    включая базовую информацию, отработанные часы, дополнительные смены,
    компоненты премии и итоговую сумму.

    Attributes:
        user: Экземпляр пользователя с моделью Employee
        current_month_name: Название текущего месяца
        current_year: Текущий год
        pay_rate: Часовая тарифная ставка (ЧТС)

        working_days: Количество отработанных дней
        total_working_hours: Общее количество отработанных часов
        regular_hours: Обычные рабочие часы (дневные, не праздничные)
        night_hours: Ночные часы (22:00-06:00)
        holiday_hours: Дневные часы в праздничные дни
        night_holiday_hours: Ночные часы в праздничные дни
        holiday_days_worked: Список отработанных праздничных дней

        additional_shift_hours: Часы дополнительных смен
        additional_shift_holiday_hours: Праздничные часы доп. смен
        additional_shift_night_hours: Ночные часы доп. смен
        additional_shift_night_holiday_hours: Ночные праздничные часы доп. смен
        additional_shift_days_worked: Список дней с доп. сменами

        base_salary: Базовая зарплата (без премии)
        additional_shift_salary: Зарплата за дополнительные смены
        additional_shift_rate: Ставка для дополнительных смен
        additional_shift_holiday_rate: Праздничная ставка доп. смен
        additional_shift_night_rate: Ночная ставка доп. смен
        additional_shift_night_holiday_rate: Ночная праздничная ставка доп. смен

        csi_premium_amount: Сумма премии CSI
        flr_premium_amount: Сумма премии FLR
        gok_premium_amount: Сумма премии GOK
        target_premium_amount: Сумма премии за выполнение цели
        discipline_premium_amount: Сумма премии за дисциплину
        tests_premium_amount: Сумма премии за тесты
        thanks_premium_amount: Сумма премии за благодарности
        tutors_premium_amount: Сумма премии за наставничество
        head_adjust_premium_amount: Корректировка премии руководителем
        premium_amount: Общая сумма премии

        total_salary: Итоговая зарплата

        calculation_time: Время проведения расчета
        premium_updated_at: Время последнего обновления премии
    """

    # Базовая информация
    user: Employee
    current_month_name: str
    current_year: int
    pay_rate: float

    # Рабочие часы
    working_days: float
    total_working_hours: float
    regular_hours: float
    night_hours: float
    holiday_hours: float
    night_holiday_hours: float
    holiday_days_worked: List[str]

    # Дополнительные смены
    additional_shift_hours: float
    additional_shift_holiday_hours: float
    additional_shift_night_hours: float
    additional_shift_night_holiday_hours: float
    additional_shift_days_worked: List[str]

    # Компоненты зарплаты
    base_salary: float
    additional_shift_salary: float
    additional_shift_rate: float
    additional_shift_holiday_rate: float
    additional_shift_night_rate: float
    additional_shift_night_holiday_rate: float

    # Премия
    csi_premium_amount: float
    flr_premium_amount: float
    gok_premium_amount: float
    target_premium_amount: float
    discipline_premium_amount: float
    tests_premium_amount: float
    thanks_premium_amount: float
    tutors_premium_amount: float
    head_adjust_premium_amount: float
    premium_amount: float

    # Финальный подсчет зарплаты
    total_salary: float

    # Мета
    calculation_time: datetime.datetime
    premium_updated_at: Optional[datetime.datetime]


class SalaryCalculator:
    """Сервис для расчета зарплаты сотрудников.

    Предоставляет функциональность для полного расчета заработной платы,
    включая обработку графика работы, подсчет ночных и праздничных часов,
    дополнительных смен и всех видов премий.

    Основные возможности:
        - Расчет ночных часов (22:00-06:00 по местному времени)
        - Обработка данных графика работы и дополнительных смен
        - Подсчет базовой зарплаты с учетом различных коэффициентов
        - Расчет премий для специалистов и руководителей
        - Учет праздничных дней согласно производственному календарю

    Note:
        Все расчеты выполняются асинхронно для работы с внешними API
        (производственный календарь).
    """

    @staticmethod
    def _calculate_night_hours(
        start_hour: int, start_min: int, end_hour: int, end_min: int
    ) -> float:
        """Рассчитывает количество ночных часов в рабочей смене.

        Определяет количество часов, отработанных в ночное время
        (с 22:00 до 06:00 по локальному времени). Алгоритм корректно
        обрабатывает смены, переходящие через полночь.

        Args:
            start_hour: Час начала смены (0-23)
            start_min: Минута начала смены (0-59)
            end_hour: Час окончания смены (0-23)
            end_min: Минута окончания смены (0-59)

        Returns:
            Количество ночных часов в смене (в часах с плавающей точкой)

        Examples:
            Смена с 20:00 до 08:00:
            >>> _calculate_night_hours(20, 0, 8, 0)
            8.0

            Смена с 23:00 до 02:00:
            >>> _calculate_night_hours(23, 0, 2, 0)
            3.0

            Смена с 10:00 до 18:00:
            >>> _calculate_night_hours(10, 0, 18, 0)
            0.0

        Note:
            Ночными часами считается период с 22:00 до 06:00 включительно.
            Если смена проходит полностью в дневное время, возвращается 0.0.
        """
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        if end_minutes < start_minutes:
            end_minutes += 24 * 60

        night_start = 22 * 60  # 22:00 в минутах
        night_end = 6 * 60  # 06:00 в минутах (следующий день)

        total_night_minutes = 0

        # Проверяем рабочие часы в первый день (22:00-24:00)
        first_day_night_start = night_start
        first_day_night_end = 24 * 60  # Полночь

        if start_minutes < first_day_night_end and end_minutes > first_day_night_start:
            overlap_start = max(start_minutes, first_day_night_start)
            overlap_end = min(end_minutes, first_day_night_end)
            if overlap_end > overlap_start:
                total_night_minutes += overlap_end - overlap_start

        # Проверяем ночные часы во второй день (00:00-06:00)
        if end_minutes > 24 * 60:  # Смена продолжается на следующий день
            second_day_start = 24 * 60
            second_day_end = end_minutes
            second_day_night_start = 24 * 60  # 00:00 следующего дня
            second_day_night_end = 24 * 60 + night_end  # 06:00 следующего дня

            if (
                second_day_start < second_day_night_end
                and second_day_end > second_day_night_start
            ):
                overlap_start = max(second_day_start, second_day_night_start)
                overlap_end = min(second_day_end, second_day_night_end)
                if overlap_end > overlap_start:
                    total_night_minutes += overlap_end - overlap_start

        # Проверяем ночные часы в начале того же дня (00:00-06:00)
        # Это для случаев типа 03:00-09:00, которые не переходят через полночь
        elif start_minutes < night_end and end_minutes > 0:
            # Диапазон находится в пределах одного дня, но может попадать в утренние ночные часы
            overlap_start = max(start_minutes, 0)
            overlap_end = min(end_minutes, night_end)
            if overlap_end > overlap_start:
                total_night_minutes += overlap_end - overlap_start

        return total_night_minutes / 60  # Конвертируем в часы

    @staticmethod
    async def _process_schedule_data(
        schedule_data: Dict[str, str],
        now: datetime.datetime,
        is_additional_shift: bool = False,
    ) -> Tuple[float, float, float, float, float, List[str]]:
        """Обрабатывает данные графика работы для расчета часов и дней.

        Анализирует график работы сотрудника, вычисляет общие, ночные и
        праздничные часы с учетом производственного календаря. Поддерживает
        обработку как основных смен, так и дополнительных.

        Args:
            schedule_data: Словарь с данными графика {день: время_работы}
            now: Текущая дата и время для определения месяца и года
            is_additional_shift: Флаг дополнительной смены

        Returns:
            Кортеж из 6 элементов:
                - total_hours: Общее количество отработанных часов
                - night_hours: Количество ночных часов (обычных дней)
                - holiday_hours: Количество праздничных часов (дневных)
                - night_holiday_hours: Количество ночных праздничных часов
                - working_days: Количество отработанных дней
                - days_worked: Список строк с описанием отработанных дней

        Raises:
            Exception: При ошибке обращения к производственному календарю

        Note:
            Метод учитывает время обеда при расчете рабочих часов и
            пропорционально корректирует ночные часы. Использует внешний
            API производственного календаря для определения праздничных дней.
        """
        total_hours = 0.0
        night_hours = 0.0
        holiday_hours = 0.0
        night_holiday_hours = 0.0
        working_days = 0
        days_worked = []

        for day, schedule_time in schedule_data.items():
            if schedule_time and schedule_time not in ["Не указано", "В", "О"]:
                # Используем ScheduleAnalyzer для подсчета рабочих часов (с учетом обеда)
                day_hours = ScheduleAnalyzer.calculate_work_hours(schedule_time)

                if day_hours > 0:
                    # Парсим временные диапазоны для подсчета ночных часов
                    time_pattern = r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})"
                    time_matches = re.findall(time_pattern, schedule_time)

                    shift_night_hours = 0.0
                    total_raw_hours = 0.0

                    # Обрабатываем каждый временной диапазон для ночных часов
                    for match in time_matches:
                        start_hour, start_min, end_hour, end_min = map(int, match)
                        start_minutes = start_hour * 60 + start_min
                        end_minutes = end_hour * 60 + end_min

                        if end_minutes < start_minutes:
                            end_minutes += 24 * 60

                        range_hours = (end_minutes - start_minutes) / 60
                        total_raw_hours += range_hours

                        # Считаем ночные часы для этого диапазона
                        range_night_hours = SalaryCalculator._calculate_night_hours(
                            start_hour, start_min, end_hour, end_min
                        )
                        shift_night_hours += range_night_hours

                    # Если был вычет на обед, пропорционально уменьшаем ночные часы
                    if total_raw_hours > day_hours and shift_night_hours > 0:
                        shift_night_hours = shift_night_hours * (
                            day_hours / total_raw_hours
                        )

                    # Проверка на праздничный день
                    try:
                        work_date = datetime.date(now.year, now.month, int(day))
                        is_holiday = await production_calendar.is_holiday(work_date)
                        holiday_name = await production_calendar.get_holiday_name(
                            work_date
                        )

                        if is_holiday and holiday_name:
                            # Разделяем праздничные часы на дневные и ночные
                            holiday_hours += day_hours - shift_night_hours
                            night_holiday_hours += shift_night_hours
                            if is_additional_shift:
                                days_worked.append(
                                    f"{day} - {holiday_name} (+{day_hours:.0f}ч доп.)"
                                )
                            else:
                                days_worked.append(
                                    f"{day} - {holiday_name} (+{day_hours:.0f}ч)"
                                )
                        else:
                            night_hours += shift_night_hours
                            if is_additional_shift:
                                days_worked.append(
                                    f"{day} - Доп. смена (+{day_hours:.0f}ч)"
                                )
                    except (ValueError, Exception):
                        night_hours += shift_night_hours
                        if is_additional_shift:
                            days_worked.append(
                                f"{day} - Доп. смена (+{day_hours:.0f}ч)"
                            )

                    total_hours += day_hours
                    working_days += 1

        return (
            total_hours,
            night_hours,
            holiday_hours,
            night_holiday_hours,
            working_days,
            days_worked,
        )

    @classmethod
    async def calculate_salary(
        cls, user: Employee, premium_data, current_month: Optional[str] = None
    ) -> SalaryCalculationResult:
        """Выполняет полный расчет зарплаты сотрудника за месяц.

        Основной метод для расчета заработной платы, который объединяет
        все компоненты: базовую зарплату, дополнительные смены, премии
        и создает подробный отчет о расчетах.

        Args:
            user: Объект сотрудника из базы данных с информацией о
                должности, подразделении и ФИО
            premium_data: Объект с данными о премиях (SpecPremium или HeadPremium)
                содержащий процентные значения всех видов премий
            current_month: Название месяца для расчета (по умолчанию текущий)

        Returns:
            SalaryCalculationResult: Полный результат расчета зарплаты
                с детализацией по всем компонентам

        Raises:
            ValueError: Если не найдена ЧТС для подразделения и должности
            Exception: При ошибках парсинга графика или других расчетных ошибках

        Note:
            - Использует производственный календарь для определения праздников
            - Различает расчет премий для специалистов и руководителей
            - Учитывает часовой пояс +5 для корректного времени расчета
            - Автоматически вычитает время обеда из рабочих часов
        """
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5)))
        current_month_name = current_month or russian_months[now.month]

        # Получаем ЧТС
        pay_rate = PayRateService.get_pay_rate(user.division, user.position)
        if pay_rate == 0.0:
            raise ValueError(
                f"Не найдено ЧТС для '{user.division}' на позиции '{user.position}'"
            )

        try:
            schedule_data, additional_shifts_data = (
                schedule_parser.get_user_schedule_with_additional_shifts(
                    user.fullname, current_month_name, user.division
                )
            )
        except Exception as e:
            raise Exception(f"Произошла ошибка при расчете: {e}")

        (
            total_working_hours,
            night_hours,
            holiday_hours,
            night_holiday_hours,
            working_days,
            holiday_days_worked,
        ) = await cls._process_schedule_data(
            schedule_data, now, is_additional_shift=False
        )

        # Процессим дополнительные смены
        (
            additional_shift_hours,
            additional_shift_night_hours,
            additional_shift_holiday_hours,
            additional_shift_night_holiday_hours,
            _,
            additional_shift_days_worked,
        ) = await cls._process_schedule_data(
            additional_shifts_data, now, is_additional_shift=True
        )

        # Считаем обычные часы (исключая ночные часы и праздники их расчета)
        regular_hours = (
            total_working_hours - holiday_hours - night_hours - night_holiday_hours
        )
        regular_additional_shift_hours = (
            additional_shift_hours
            - additional_shift_holiday_hours
            - additional_shift_night_hours
            - additional_shift_night_holiday_hours
        )

        # Считаем базовую зарплату
        base_salary = (
            (regular_hours * pay_rate)
            + (holiday_hours * pay_rate * PayRateService.get_holiday_multiplier())
            + (night_hours * pay_rate * PayRateService.get_night_multiplier())
            + (
                night_holiday_hours
                * pay_rate
                * PayRateService.get_night_holiday_multiplier()
            )
        )

        # Считаем зарплату за дополнительные смены
        additional_shift_rate = (
            pay_rate * PayRateService.get_additional_shift_multiplier()
        )
        additional_shift_holiday_rate = (
            additional_shift_rate * PayRateService.get_holiday_multiplier()
        )
        additional_shift_night_rate = (
            additional_shift_rate * PayRateService.get_night_multiplier()
        )
        additional_shift_night_holiday_rate = (
            additional_shift_rate * PayRateService.get_night_holiday_multiplier()
        )

        additional_shift_salary = (
            (regular_additional_shift_hours * additional_shift_rate)
            + (additional_shift_holiday_hours * additional_shift_holiday_rate)
            + (additional_shift_night_hours * additional_shift_night_rate)
            + (
                additional_shift_night_holiday_hours
                * additional_shift_night_holiday_rate
            )
        )

        # Считаем индивидуальную сумму для каждого показателя премии (основываясь на базовой зарплате)
        # Проверяем тип премиум данных (HeadPremium vs SpecPremium)
        is_head_premium = hasattr(premium_data, "head_adjust") and not hasattr(
            premium_data, "csi_premium"
        )

        if is_head_premium:
            # Для руководителей - только FLR, GOK, цель и корректировка руководителя
            csi_premium_amount = 0
            flr_premium_amount = base_salary * ((premium_data.flr_premium or 0) / 100)
            gok_premium_amount = base_salary * ((premium_data.gok_premium or 0) / 100)
            target_premium_amount = base_salary * (
                (premium_data.target_premium or 0) / 100
            )
            discipline_premium_amount = 0
            tests_premium_amount = 0
            thanks_premium_amount = 0
            tutors_premium_amount = 0
            head_adjust_premium_amount = base_salary * (
                (premium_data.head_adjust or 0) / 100
            )
        else:
            # Для специалистов - все показатели
            csi_premium_amount = base_salary * ((premium_data.csi_premium or 0) / 100)
            flr_premium_amount = base_salary * ((premium_data.flr_premium or 0) / 100)
            gok_premium_amount = base_salary * ((premium_data.gok_premium or 0) / 100)
            target_premium_amount = base_salary * (
                (premium_data.target_premium or 0) / 100
            )
            discipline_premium_amount = base_salary * (
                (premium_data.discipline_premium or 0) / 100
            )
            tests_premium_amount = base_salary * (
                (premium_data.tests_premium or 0) / 100
            )
            thanks_premium_amount = base_salary * (
                (premium_data.thanks_premium or 0) / 100
            )
            tutors_premium_amount = base_salary * (
                (premium_data.tutors_premium or 0) / 100
            )
            head_adjust_premium_amount = base_salary * (
                (premium_data.head_adjust_premium or 0) / 100
            )

        # Считаем общую сумму премии
        premium_multiplier = (premium_data.total_premium or 0) / 100
        premium_amount = base_salary * premium_multiplier
        total_salary = base_salary + premium_amount + additional_shift_salary

        return SalaryCalculationResult(
            user=user,
            current_month_name=current_month_name,
            current_year=now.year,
            pay_rate=pay_rate,
            working_days=working_days,
            total_working_hours=total_working_hours,
            regular_hours=regular_hours,
            night_hours=night_hours,
            holiday_hours=holiday_hours,
            night_holiday_hours=night_holiday_hours,
            holiday_days_worked=holiday_days_worked,
            additional_shift_hours=additional_shift_hours,
            additional_shift_holiday_hours=additional_shift_holiday_hours,
            additional_shift_night_hours=additional_shift_night_hours,
            additional_shift_night_holiday_hours=additional_shift_night_holiday_hours,
            additional_shift_days_worked=additional_shift_days_worked,
            base_salary=base_salary,
            additional_shift_salary=additional_shift_salary,
            additional_shift_rate=additional_shift_rate,
            additional_shift_holiday_rate=additional_shift_holiday_rate,
            additional_shift_night_rate=additional_shift_night_rate,
            additional_shift_night_holiday_rate=additional_shift_night_holiday_rate,
            csi_premium_amount=csi_premium_amount,
            flr_premium_amount=flr_premium_amount,
            gok_premium_amount=gok_premium_amount,
            target_premium_amount=target_premium_amount,
            discipline_premium_amount=discipline_premium_amount,
            tests_premium_amount=tests_premium_amount,
            thanks_premium_amount=thanks_premium_amount,
            tutors_premium_amount=tutors_premium_amount,
            head_adjust_premium_amount=head_adjust_premium_amount,
            premium_amount=premium_amount,
            total_salary=total_salary,
            calculation_time=now,
            premium_updated_at=getattr(premium_data, "updated_at", None),
        )
