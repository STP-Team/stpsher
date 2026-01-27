import datetime
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from stp_database.models.STP import Employee
from stp_database.repo.STP import MainRequestsRepo

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
        additional_shift_rate: Единая ставка для всех дополнительных смен (2x + премия пользователя)
        remote_work_compensation_amount: Компенсация за удаленную работу (35₽ за рабочий день)

        csat_premium_amount: Сумма премии CSAT (для специалистов)
        aht_premium_amount: Сумма премии AHT
        flr_premium_amount: Сумма премии FLR (только для руководителей)
        gok_premium_amount: Сумма премии GOK
        premium_amount: Общая сумма премии

        total_salary: Итоговая зарплата

        exchange_income: Доходы от биржевых операций за месяц
        exchange_expenses: Расходы на биржевые операции за месяц
        exchange_net_profit: Чистая прибыль от биржевых операций (доходы - расходы)
        total_with_exchanges: Итоговая зарплата с учетом биржевых операций

        first_half_hours: Часы работы в первой половине месяца (1-15 числа)
        advance_payment: Аванс (первая половина месяца × ставка)
        main_payment: Основная часть зарплаты (полная зарплата - аванс)

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
    night_bonus_amount: float
    holiday_bonus_amount: float
    night_holiday_bonus_amount: float
    additional_shift_salary: float
    additional_shift_rate: float
    remote_work_compensation_amount: float

    # Премия
    csat_premium_amount: float
    aht_premium_amount: float
    flr_premium_amount: float
    gok_premium_amount: float
    premium_amount: float

    # Финальный подсчет зарплаты
    total_salary: float

    # Биржевые операции
    exchange_income: float
    exchange_expenses: float
    exchange_net_profit: float
    total_with_exchanges: float

    # Аванс и основная часть зарплаты
    first_half_hours: float
    advance_payment: float
    main_payment: float

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
        - Дополнительные смены: двойная оплата + индивидуальная премия (без доплат за ночь/праздники)

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
        target_year: int,
        target_month: int,
        is_additional_shift: bool = False,
    ) -> Tuple[float, float, float, float, float, List[str]]:
        """Обрабатывает данные графика работы для расчета часов и дней.

        Анализирует график работы сотрудника, вычисляет общие, ночные и
        праздничные часы с учетом производственного календаря. Поддерживает
        обработку как основных смен, так и дополнительных.

        Args:
            schedule_data: Словарь с данными графика {день: время_работы}
            target_year: Год для расчета
            target_month: Месяц для расчета (1-12)
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
                        # Извлекаем число из строки дня (формат: "1 (Пн)", "2 (Вт)", etc.)
                        day_match = re.search(r"(\d+)", day)
                        if not day_match:
                            raise ValueError(
                                f"Could not extract day number from: {day}"
                            )
                        day_num = int(day_match.group(1))

                        work_date = datetime.date(target_year, target_month, day_num)
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

    @staticmethod
    def _calculate_first_half_hours(schedule_data: Dict[str, str]) -> float:
        """Рассчитывает количество рабочих часов в первой половине месяца (1-15 числа).

        Args:
            schedule_data: Словарь с данными графика {день: время_работы}

        Returns:
            Количество рабочих часов в первой половине месяца
        """
        first_half_hours = 0.0

        for day, schedule_time in schedule_data.items():
            try:
                # Извлекаем число из начала строки (формат: "1 (Сб)", "2 (Вс)", etc.)
                day_parts = day.split(" ")
                day_num = int(day_parts[0]) if day_parts[0].isdigit() else None

                if day_num is None:
                    continue

                # Проверяем, что день в первой половине месяца (1-15 включительно)
                if 1 <= day_num <= 15:
                    # Проверяем что schedule_time валидное и не является отпуском/выходным
                    if (
                        schedule_time
                        and schedule_time
                        not in [None, "Не указано", "В", "О", "ОТПУСК"]
                        and isinstance(schedule_time, str)
                    ):
                        # Используем ScheduleAnalyzer для подсчета рабочих часов (с учетом обеда)
                        day_hours = ScheduleAnalyzer.calculate_work_hours(schedule_time)
                        first_half_hours += day_hours
            except (ValueError, TypeError):
                # Пропускаем дни, которые не являются числами
                continue

        return first_half_hours

    @classmethod
    async def _calculate_first_half_salary(
        cls,
        schedule_data: Dict[str, str],
        pay_rate: float,
        target_year: int,
        target_month: int,
    ) -> float:
        """Рассчитывает полную стоимость зарплаты за первую половину месяца (1-15 числа) включая доплаты.

        Args:
            schedule_data: Словарь с данными графика {день: время_работы}
            pay_rate: Часовая тарифная ставка
            target_year: Год для расчета
            target_month: Месяц для расчета (1-12)

        Returns:
            Полная стоимость зарплаты за первую половину месяца с учетом доплат
        """
        first_half_salary = 0.0

        for day, schedule_time in schedule_data.items():
            try:
                # Извлекаем число из начала строки (формат: "1 (Сб)", "2 (Вс)", etc.)
                day_parts = day.split(" ")
                day_num = int(day_parts[0]) if day_parts[0].isdigit() else None

                if day_num is None:
                    continue

                # Проверяем, что день в первой половине месяца (1-15 включительно)
                if 1 <= day_num <= 15:
                    # Проверяем что schedule_time валидное и не является отпуском/выходным
                    if (
                        schedule_time
                        and schedule_time
                        not in [None, "Не указано", "В", "О", "ОТПУСК"]
                        and isinstance(schedule_time, str)
                    ):
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
                                start_hour, start_min, end_hour, end_min = map(
                                    int, match
                                )
                                start_minutes = start_hour * 60 + start_min
                                end_minutes = end_hour * 60 + end_min

                                if end_minutes < start_minutes:
                                    end_minutes += 24 * 60

                                range_hours = (end_minutes - start_minutes) / 60
                                total_raw_hours += range_hours

                                # Считаем ночные часы для этого диапазона
                                range_night_hours = cls._calculate_night_hours(
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
                                work_date = datetime.date(
                                    target_year, target_month, day_num
                                )
                                is_holiday = await production_calendar.is_holiday(
                                    work_date
                                )

                                if is_holiday:
                                    # Праздничные часы: дневные × 2.0 + ночные × 2.4
                                    holiday_day_hours = day_hours - shift_night_hours
                                    day_salary = (
                                        holiday_day_hours
                                        * pay_rate
                                        * PayRateService.get_holiday_multiplier()
                                    ) + (
                                        shift_night_hours
                                        * pay_rate
                                        * PayRateService.get_night_holiday_multiplier()
                                    )
                                else:
                                    # Обычные часы: дневные × 1.0 + ночные × 1.2
                                    regular_day_hours = day_hours - shift_night_hours
                                    day_salary = (regular_day_hours * pay_rate) + (
                                        shift_night_hours
                                        * pay_rate
                                        * PayRateService.get_night_multiplier()
                                    )
                            except (ValueError, Exception):
                                # Если ошибка с календарем, считаем как обычный день
                                regular_day_hours = day_hours - shift_night_hours
                                day_salary = (regular_day_hours * pay_rate) + (
                                    shift_night_hours
                                    * pay_rate
                                    * PayRateService.get_night_multiplier()
                                )

                            first_half_salary += day_salary

            except (ValueError, TypeError):
                # Пропускаем дни, которые не являются числами
                continue

        return first_half_salary

    @classmethod
    async def calculate_salary(
        cls,
        user: Employee,
        premium_data,
        stp_repo: MainRequestsRepo,
        current_month: Optional[str] = None,
        current_year: Optional[int] = None,
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
            stp_repo: Репозиторий для работы с базой данных STP
            current_month: Название месяца для расчета (по умолчанию текущий)
            current_year: Год для расчета (по умолчанию текущий)

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

        # Определяем год и номер месяца для выбранного месяца
        month_to_num = {name: num for num, name in russian_months.items()}
        selected_month_num = month_to_num.get(current_month_name.lower(), now.month)

        if current_year:
            # Используем переданный год
            target_year = current_year
        elif current_month:
            # Обратная совместимость: если год не передан, определяем его логически
            # Если выбранный месяц больше текущего, это прошлый год
            if selected_month_num > now.month:
                target_year = now.year - 1
            else:
                target_year = now.year
        else:
            target_year = now.year

        # Получаем ЧТС
        pay_rate = PayRateService.get_pay_rate(user.division, user.position)
        if pay_rate == 0.0:
            raise ValueError(
                f"Не найдено ЧТС для '{user.division}' на позиции '{user.position}'"
            )

        try:
            schedule_data, additional_shifts_data = (
                schedule_parser.get_user_schedule_with_additional_shifts(
                    user.fullname, current_month_name, user.division, target_year
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
            schedule_data, target_year, selected_month_num, is_additional_shift=False
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
            additional_shifts_data,
            target_year,
            selected_month_num,
            is_additional_shift=True,
        )

        # Считаем обычные часы (исключая ночные часы и праздники их расчета)
        regular_hours = (
            total_working_hours - holiday_hours - night_hours - night_holiday_hours
        )

        # Базовая зарплата (все часы по базовой ставке, без доплат)
        # Премия считается от базовой ставки всех часов
        base_salary = total_working_hours * pay_rate

        # Доплаты (не облагаются премией)
        night_bonus_amount = night_hours * pay_rate * 0.2  # 20% за ночные часы
        holiday_bonus_amount = (
            holiday_hours * pay_rate * 1.0
        )  # 100% за праздничные дни (двойная оплата)
        night_holiday_bonus_amount = (
            night_holiday_hours * pay_rate * 0.2
        )  # 20% за ночные часы в праздники

        # Считаем зарплату за дополнительные смены
        # Используем двойную ставку + собственную премию пользователя (вместо фиксированных 63%)
        additional_shift_premium_multiplier = 1 + (
            (premium_data.total_premium or 0) / 100
        )
        additional_shift_rate = pay_rate * 2.0 * additional_shift_premium_multiplier

        # Все часы дополнительных смен оплачиваются по единой ставке (без доплат за ночь/праздники)
        additional_shift_salary = additional_shift_hours * additional_shift_rate

        # Считаем компенсацию за удаленную работу
        remote_work_compensation_amount = (
            working_days * PayRateService.get_remote_work_compensation()
        )

        # Считаем общую сумму премии (основываясь на базовой зарплате за весь месяц)
        # Проверяем тип премиум данных по роли пользователя
        is_head_premium = user.role == 2

        if is_head_premium:
            # Для руководителей: FLR, GOK, AHT
            csat_premium_amount = 0
            flr_premium_amount = base_salary * ((premium_data.flr_premium or 0) / 100)
            gok_premium_amount = base_salary * ((premium_data.gok_premium or 0) / 100)
            aht_premium_amount = base_salary * ((premium_data.aht_premium or 0) / 100)
        else:
            # Для специалистов: CSAT, GOK, AHT
            csat_premium_amount = base_salary * ((premium_data.csat_premium or 0) / 100)
            flr_premium_amount = 0
            gok_premium_amount = base_salary * ((premium_data.gok_premium or 0) / 100)
            aht_premium_amount = base_salary * ((premium_data.aht_premium or 0) / 100)

        # Считаем общую сумму премии
        premium_multiplier = (premium_data.total_premium or 0) / 100
        premium_amount = base_salary * premium_multiplier

        # Считаем часы и полную стоимость первой половины месяца для аванса
        first_half_hours = cls._calculate_first_half_hours(schedule_data)
        # Аванс = полная стоимость первой половины месяца (включая ночные и праздничные доплаты)
        advance_payment = await cls._calculate_first_half_salary(
            schedule_data, pay_rate, target_year, selected_month_num
        )

        # Рассчитываем основную часть зарплаты отдельно (вторая половина месяца)
        # Основная часть включает: базовую зарплату второй половины + премии + доп. смены + компенсация
        # Премии начисляются за весь месяц, а не только за вторую половину
        second_half_hours = total_working_hours - first_half_hours
        second_half_base_salary = second_half_hours * pay_rate

        main_payment = (
            second_half_base_salary  # Базовая зарплата за вторую половину
            + premium_amount  # Все премии за весь месяц
            + additional_shift_salary  # Дополнительные смены
            + remote_work_compensation_amount  # Компенсация за удаленную работу
        )

        # Полная зарплата = аванс + основная часть
        total_salary = advance_payment + main_payment

        # Расчет биржевых операций за выбранный месяц
        # Создаем диапазон дат для выбранного месяца
        start_date = datetime.datetime(target_year, selected_month_num, 1)

        # Конец месяца
        if selected_month_num == 12:
            end_date = datetime.datetime(target_year + 1, 1, 1)
        else:
            end_date = datetime.datetime(target_year, selected_month_num + 1, 1)

        # Получаем финансовую статистику биржевых операций за период
        exchange_income = await stp_repo.exchange.get_user_total_gain(
            user_id=user.user_id, start_date=start_date, end_date=end_date
        )

        exchange_expenses = await stp_repo.exchange.get_user_total_loss(
            user_id=user.user_id, start_date=start_date, end_date=end_date
        )

        # Вычисляем чистую прибыль от биржевых операций
        exchange_net_profit = exchange_income - exchange_expenses

        # Итоговая сумма с учетом биржевых операций
        total_with_exchanges = total_salary + exchange_net_profit

        return SalaryCalculationResult(
            user=user,
            current_month_name=current_month_name,
            current_year=target_year,
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
            night_bonus_amount=night_bonus_amount,
            holiday_bonus_amount=holiday_bonus_amount,
            night_holiday_bonus_amount=night_holiday_bonus_amount,
            additional_shift_salary=additional_shift_salary,
            additional_shift_rate=additional_shift_rate,
            remote_work_compensation_amount=remote_work_compensation_amount,
            csat_premium_amount=csat_premium_amount,
            aht_premium_amount=aht_premium_amount,
            flr_premium_amount=flr_premium_amount,
            gok_premium_amount=gok_premium_amount,
            premium_amount=premium_amount,
            total_salary=total_salary,
            exchange_income=exchange_income,
            exchange_expenses=exchange_expenses,
            exchange_net_profit=exchange_net_profit,
            total_with_exchanges=total_with_exchanges,
            first_half_hours=first_half_hours,
            advance_payment=advance_payment,
            main_payment=main_payment,
            calculation_time=now,
            premium_updated_at=getattr(premium_data, "updated_at", None),
        )
