import datetime

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from infrastructure.api.production_calendar import production_calendar
from infrastructure.database.models import Employee
from infrastructure.database.repo.KPI.requests import KPIRequestsRepo
from tgbot.keyboards.user.kpi import kpi_calculator_kb, kpi_kb, kpi_salary_kb
from tgbot.keyboards.user.main import MainMenu
from tgbot.misc.dicts import russian_months
from tgbot.services.schedule import ScheduleParser

user_kpi_router = Router()
user_kpi_router.message.filter(F.chat.type == "private")
user_kpi_router.callback_query.filter(F.message.chat.type == "private")


@user_kpi_router.callback_query(MainMenu.filter(F.menu == "kpi"))
async def user_kpi_cb(
    callback: CallbackQuery, user: Employee, kpi_repo: KPIRequestsRepo
):
    premium = await kpi_repo.spec_premium.get_premium(fullname=user.fullname)
    if premium is None:
        await callback.message.edit_text(
            """🌟 <b>Показатели</b>

Не смог найти твои показатели в премиуме :(""",
            reply_markup=kpi_kb(),
        )
        return

    def format_value(value, suffix=""):
        return f"{value}{suffix}" if value is not None else "—"

    def format_percentage(value):
        return f"{value}%" if value is not None else "—"

    message_text = f"""🌟 <b>Показатели</b>

📊 <b>Оценка клиента - {format_percentage(premium.csi_premium)}</b>
<blockquote>Факт: {format_value(premium.csi)}
План: {format_value(premium.csi_normative)}  </blockquote>

🎯 <b>Отклик</b>
<blockquote>Факт: {format_value(premium.csi_response)}
План: {format_value(round(premium.csi_response_normative))}</blockquote>

🔧 <b>FLR - {format_percentage(premium.flr_premium)}</b>
<blockquote>Факт: {format_value(premium.flr)}
План: {format_value(premium.flr_normative)}</blockquote>

⚖️ <b>ГОК - {format_percentage(premium.gok_premium)}</b>
<blockquote>Факт: {format_value(premium.gok)}
План: {format_value(premium.gok_normative)}</blockquote>

🎯 <b>Цель - {format_percentage(premium.target_premium)}</b>
<blockquote>Тип: {premium.target_type or "—"}
Факт: {format_value(premium.target)}
План: {format_value(round(premium.target_goal_first))} / {format_value(round(premium.target_goal_second))}</blockquote>

💼 <b>Дополнительно</b>
<blockquote>Дисциплина: {format_percentage(premium.discipline_premium)}
Тестирование: {format_percentage(premium.tests_premium)}
Благодарности: {format_percentage(premium.thanks_premium)}
Наставничество: {format_percentage(premium.tutors_premium)}
Ручная правка: {format_percentage(premium.head_adjust_premium)}</blockquote>

💰 <b>Итого:</b>
<b>Общая премия: {format_percentage(premium.total_premium)}</b>

{"📈 Всего чатов: " + format_value(premium.contacts_count) if user.division == "НЦК" else "📈 Всего звонков: " + format_value(premium.contacts_count)}
{"⏰ Задержка: " + format_value(premium.delay, " сек") if user.division != "НЦК" else ""}
<i>Выгружено: {premium.updated_at.replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=5))).strftime("%d.%m.%y %H:%M") if premium.updated_at else "—"}</i>
<i>Обновлено: {datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5))).strftime("%d.%m.%y %H:%M")}</i>"""

    try:
        await callback.message.edit_text(message_text, reply_markup=kpi_kb())
    except TelegramBadRequest:
        await callback.answer("Обновлений нет")


@user_kpi_router.callback_query(MainMenu.filter(F.menu == "kpi_calculator"))
async def user_kpi_calculator_cb(
    callback: CallbackQuery, user: Employee, kpi_repo: KPIRequestsRepo
):
    user_premium = await kpi_repo.spec_premium.get_premium(fullname=user.fullname)

    if user_premium is None:
        await callback.message.edit_text(
            """🧮 <b>Калькулятор KPI</b>

Не смог найти твои показатели в премиуме :(""",
            reply_markup=kpi_calculator_kb(),
        )
        return

    def calculate_csi_needed(division: str, current_csi, normative):
        if normative == 0 or normative is None:
            return "—"

        current_csi = current_csi or 0

        results = []

        if division == "НЦК":
            thresholds = [
                (101, 20, "≥ 101%"),
                (100.5, 15, "≥ 100,5%"),
                (100, 10, "≥ 100%"),
                (98, 5, "≥ 98%"),
                (0, 0, "&lt; 98%"),
            ]
        elif division == "НТП1":
            thresholds = [
                (101, 20, "≥ 101%"),
                (100.5, 15, "≥ 100,5%"),
                (100, 10, "≥ 100%"),
                (98, 5, "≥ 98%"),
                (0, 0, "&lt; 98%"),
            ]
        else:
            thresholds = [
                (100.8, 20, "≥ 100.8%"),
                (100.4, 15, "≥ 100.4%"),
                (100, 10, "≥ 100%"),
                (98, 5, "≥ 98%"),
                (0, 0, "&lt; 98%"),
            ]

        for threshold, premium_percent, description in thresholds:
            needed_csi = (threshold / 100) * normative

            if current_csi >= needed_csi:
                results.append(f"{premium_percent}%: ✅ ({description})")
            else:
                difference = needed_csi - current_csi
                results.append(
                    f"{premium_percent}%: {needed_csi:.3f} [+{difference:.3f}] ({description})"
                )

        return "\n".join(results)

    def calculate_flr_needed(division: str, current_flr, normative):
        if normative == 0 or normative is None:
            return "—"

        current_flr = current_flr or 0

        results = []

        if division == "НЦК":
            thresholds = [
                (103, 30, "≥ 103%"),
                (102, 25, "≥ 102%"),
                (101, 21, "≥ 101%"),
                (100, 18, "≥ 100%"),
                (95, 13, "≥ 95%"),
                (0, 8, "&lt; 95%"),
            ]
        elif division == "НТП1":
            thresholds = [
                (109, 30, "≥ 109%"),
                (106, 25, "≥ 106%"),
                (103, 21, "≥ 103%"),
                (100, 18, "≥ 100%"),
                (90, 13, "≥ 90%"),
                (0, 8, "&lt; 90%"),
            ]
        else:
            thresholds = [
                (107, 30, "≥ 107%"),
                (104, 25, "≥ 104%"),
                (102, 21, "≥ 102%"),
                (100, 18, "≥ 100%"),
                (97, 13, "≥ 97%"),
                (0, 8, "&lt; 97%"),
            ]

        for threshold, premium_percent, description in thresholds:
            needed_flr = (threshold / 100) * normative

            if current_flr >= needed_flr:
                results.append(f"{premium_percent}%: ✅ ({description})")
            else:
                difference = needed_flr - current_flr
                results.append(
                    f"{premium_percent}%: {needed_flr:.2f} [+{difference:.2f}] ({description})"
                )

        return "\n".join(results)

    def calculate_gok_needed(division: str, current_gok, normative):
        if normative == 0 or normative is None:
            return "—"

        current_gok = current_gok or 0

        results = []

        if division == "НЦК":
            thresholds = [
                (100, 17, "≥ 100%"),
                (95, 15, "≥ 95%"),
                (90, 12, "≥ 90%"),
                (85, 9, "≥ 85%"),
                (80, 5, "≥ 80%"),
                (0, 0, "&lt; 80%"),
            ]
        elif division == "НТП1":
            thresholds = [
                (100, 17, "≥ 100%"),
                (95, 15, "≥ 95%"),
                (90, 12, "≥ 90%"),
                (85, 9, "≥ 85%"),
                (80, 5, "≥ 80%"),
                (0, 0, "&lt; 80%"),
            ]
        else:
            thresholds = [
                (100, 17, "≥ 100%"),
                (95, 15, "≥ 95%"),
                (90, 12, "≥ 90%"),
                (84, 9, "≥ 84%"),
                (70, 5, "≥ 70%"),
                (0, 0, "&lt; 70%"),
            ]

        for threshold, premium_percent, description in thresholds:
            needed_gok = (threshold / 100) * normative

            if current_gok >= needed_gok:
                results.append(f"{premium_percent}%: ✅ ({description})")
            else:
                difference = needed_gok - current_gok
                results.append(
                    f"{premium_percent}%: {needed_gok:.3f} [+{difference:.3f}] ({description})"
                )

        return "\n".join(results)

    def calculate_target_needed(
        current_target,
        target_goal_first,
        target_goal_second,
        target_type=None,
    ):
        if target_goal_first is None and target_goal_second is None:
            return "—"

        current_target = current_target or 0

        # Determine if this is a sales target (higher is better) or AHT target (lower is better)
        is_sales_target = target_type and "Продажа оборудования" in target_type
        is_aht_target = target_type and "AHT" in target_type

        results = []

        # All divisions have the same target premium thresholds
        if target_goal_second and target_goal_second > 0:
            # When there's a second goal, use it as the main normative
            normative = target_goal_second

            if is_aht_target:
                # For AHT, lower is better - calculate percentage as (normative / current * 100)
                target_rate = (
                    (normative / current_target * 100) if current_target > 0 else 0
                )
            elif is_sales_target:
                # For sales, higher is better - calculate percentage as (current / normative * 100)
                target_rate = (current_target / normative * 100) if normative > 0 else 0
            else:
                # Default behavior (higher is better) - calculate percentage as (current / normative * 100)
                target_rate = (current_target / normative * 100) if normative > 0 else 0

            if target_rate > 100.01:
                results.append("28%: ✅ (≥ 100,01% - план 2 и более)")
            else:
                if is_aht_target:
                    # For AHT, we need to be lower than the target
                    needed_for_28 = normative / (100.01 / 100)
                    difference = current_target - needed_for_28
                    results.append(
                        f"28%: {needed_for_28:.2f} [-{difference:.2f}] (≥ 100,01% - план 2 и более)"
                    )
                else:
                    # For sales, we need to be higher than the target
                    needed_for_28 = (100.01 / 100) * normative
                    difference = needed_for_28 - current_target
                    results.append(
                        f"28%: {needed_for_28:.2f} [+{difference:.2f}] (≥ 100,01% - план 2 и более)"
                    )

            if target_rate >= 100.00:
                results.append("18%: ✅ (≥ 100,00% - план 1 и менее плана 2)")
            else:
                if is_aht_target:
                    needed_for_18 = normative / (100.00 / 100)
                    difference = current_target - needed_for_18
                    results.append(
                        f"18%: {needed_for_18:.2f} [-{difference:.2f}] (= 100,00% - план 1 и менее плана 2)"
                    )
                else:
                    needed_for_18 = (100.00 / 100) * normative
                    difference = needed_for_18 - current_target
                    results.append(
                        f"18%: {needed_for_18:.2f} [+{difference:.2f}] (= 100,00% - план 1 и менее плана 2)"
                    )

            if target_rate < 99.99:
                results.append("0%: — (&lt; 99,99% - менее плана 1)")
            else:
                results.append("0%: ✅ (&lt; 99,99% - менее плана 1)")

        elif target_goal_first and target_goal_first > 0:
            # When there's only first goal, use it as normative
            normative = target_goal_first

            if is_aht_target:
                # For AHT, lower is better
                target_rate = (
                    (normative / current_target * 100) if current_target > 0 else 0
                )
            elif is_sales_target:
                # For sales, higher is better
                target_rate = (current_target / normative * 100) if normative > 0 else 0
            else:
                # Default behavior (higher is better)
                target_rate = (current_target / normative * 100) if normative > 0 else 0

            if target_rate > 100.01:
                results.append("28%: ✅ (≥ 100,01% - план 2 и более)")
            else:
                if is_aht_target:
                    needed_for_28 = normative / (100.01 / 100)
                    difference = current_target - needed_for_28
                    results.append(
                        f"28%: {needed_for_28:.2f} [-{difference:.2f}] (≥ 100,01% - план 2 и более)"
                    )
                else:
                    needed_for_28 = (100.01 / 100) * normative
                    difference = needed_for_28 - current_target
                    results.append(
                        f"28%: {needed_for_28:.2f} [+{difference:.2f}] (≥ 100,01% - план 2 и более)"
                    )

            if target_rate >= 100.00:
                results.append("18%: ✅ (≥ 100,00% - план 1 и менее плана 2)")
            else:
                if is_aht_target:
                    needed_for_18 = normative / (100.00 / 100)
                    difference = current_target - needed_for_18
                    results.append(
                        f"18%: {needed_for_18:.2f} [-{difference:.2f}] (≥ 100,00% - план 1 и менее плана 2)"
                    )
                else:
                    needed_for_18 = (100.00 / 100) * normative
                    difference = needed_for_18 - current_target
                    results.append(
                        f"18%: {needed_for_18:.2f} [+{difference:.2f}] (≥ 100,00% - план 1 и менее плана 2)"
                    )

            if target_rate < 99.99:
                results.append("0%: — (&lt; 99,99% - менее плана 1)")
            else:
                results.append("0%: ✅ (&lt; 99,99% - менее плана 1)")

        return "\n".join(results)

    def format_value(value, suffix=""):
        return f"{value}{suffix}" if value is not None else "—"

    def format_percentage(value):
        return f"{value}%" if value is not None else "—"

    csi_calculation = calculate_csi_needed(
        user.division, user_premium.csi, user_premium.csi_normative
    )
    flr_calculation = calculate_flr_needed(
        user.division, user_premium.flr, user_premium.flr_normative
    )
    gok_calculation = calculate_gok_needed(
        user.division, user_premium.gok, user_premium.gok_normative
    )
    target_calculation = calculate_target_needed(
        user_premium.target,
        user_premium.target_goal_first,
        user_premium.target_goal_second,
        user_premium.target_type,
    )

    message_text = f"""🧮 <b>Калькулятор KPI</b>

📊 <b>Оценка клиента</b>
<blockquote>Текущий: {format_value(user_premium.csi)} ({format_percentage(user_premium.csi_normative_rate)})
План: {format_value(user_premium.csi_normative)}

<b>Для премии:</b>
{csi_calculation}</blockquote>

🔧 <b>FLR</b>
<blockquote>Текущий: {format_value(user_premium.flr)} ({format_percentage(user_premium.flr_normative_rate)})
План: {format_value(user_premium.flr_normative)}

<b>Для премии:</b>
{flr_calculation}</blockquote>

⚖️ <b>ГОК</b>
<blockquote>Текущий: {format_value(round(user_premium.gok))} ({format_percentage(user_premium.gok_normative_rate)})
План: {format_value(round(user_premium.gok_normative))}

<b>Для премии:</b>
{gok_calculation}</blockquote>

🎯 <b>Цель</b>
<blockquote>Факт: {format_value(user_premium.target)} ({format_percentage(round((user_premium.target_goal_first / user_premium.target * 100) if user_premium.target_type and "AHT" in user_premium.target_type and user_premium.target and user_premium.target > 0 and user_premium.target_goal_first else (user_premium.target / user_premium.target_goal_first * 100) if user_premium.target_goal_first and user_premium.target_goal_first > 0 else 0))} / {format_percentage(round((user_premium.target_goal_second / user_premium.target * 100) if user_premium.target_type and "AHT" in user_premium.target_type and user_premium.target and user_premium.target > 0 and user_premium.target_goal_second else (user_premium.target / user_premium.target_goal_second * 100) if user_premium.target_goal_second and user_premium.target_goal_second > 0 else 0))})
План: {format_value(round(user_premium.target_goal_first))} / {format_value(round(user_premium.target_goal_second))}

Требуется минимум 100 {"чатов" if user.division == "НЦК" else "звонков"} для получения премии за цель

<b>Для премии:</b>
{target_calculation}</blockquote>

<i>Данные от: {user_premium.updated_at.replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=5))).strftime("%d.%m.%y %H:%M") if user_premium.updated_at else "—"}</i>"""

    try:
        await callback.message.edit_text(message_text, reply_markup=kpi_calculator_kb())
    except TelegramBadRequest:
        await callback.answer("Обновлений нет")


@user_kpi_router.callback_query(MainMenu.filter(F.menu == "kpi_salary"))
async def user_kpi_salary_cb(
    callback: CallbackQuery, user: Employee, kpi_repo: KPIRequestsRepo
):
    user_premium = await kpi_repo.spec_premium.get_premium(fullname=user.fullname)

    if user_premium is None:
        await callback.message.edit_text(
            """💰 <b>Расчет зарплаты</b>

Не смог найти твои показатели в премиуме :(""",
            reply_markup=kpi_salary_kb(),
        )
        return

    def format_value(value, suffix=""):
        return f"{value}{suffix}" if value is not None else "—"

    def format_percentage(value):
        return f"{value}%" if value is not None else "—"

    pay_rate = 0.0
    match user.division:
        case "НЦК":
            match user.position:
                case "Специалист":
                    pay_rate = 156.7
                case "Ведущий специалист":
                    pay_rate = 164.2
                case "Эксперт":
                    pay_rate = 195.9
        case "НТП1":
            match user.position:
                case "Специалист первой линии":
                    pay_rate = 143.6
        case "НТП2":
            match user.position:
                case "Специалист второй линии":
                    pay_rate = 166
                case "Ведущий специалист второй линии":
                    pay_rate = 181
                case "Эксперт второй линии":
                    pay_rate = 195.9

    # Get current month working hours from actual schedule
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5)))
    current_month_name = russian_months[now.month]

    def calculate_night_hours(start_hour, start_min, end_hour, end_min):
        """Calculate night hours (22:00-06:00) from a work shift"""
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        # Handle overnight shifts
        if end_minutes < start_minutes:
            end_minutes += 24 * 60

        night_start = 22 * 60  # 22:00 in minutes
        night_end = 6 * 60  # 06:00 in minutes (next day)

        total_night_minutes = 0

        # Check for night hours in first day (22:00-24:00)
        first_day_night_start = night_start
        first_day_night_end = 24 * 60  # Midnight

        if start_minutes < first_day_night_end and end_minutes > first_day_night_start:
            overlap_start = max(start_minutes, first_day_night_start)
            overlap_end = min(end_minutes, first_day_night_end)
            if overlap_end > overlap_start:
                total_night_minutes += overlap_end - overlap_start

        # Check for night hours in second day (00:00-06:00)
        if end_minutes > 24 * 60:  # Shift continues to next day
            second_day_start = 24 * 60
            second_day_end = end_minutes
            second_day_night_start = 24 * 60  # 00:00 next day
            second_day_night_end = 24 * 60 + night_end  # 06:00 next day

            if (
                second_day_start < second_day_night_end
                and second_day_end > second_day_night_start
            ):
                overlap_start = max(second_day_start, second_day_night_start)
                overlap_end = min(second_day_end, second_day_night_end)
                if overlap_end > overlap_start:
                    total_night_minutes += overlap_end - overlap_start

        return total_night_minutes / 60  # Convert to hours

    # Get actual schedule data with additional shifts detection
    schedule_parser = ScheduleParser()
    try:
        schedule_data, additional_shifts_data = (
            schedule_parser.get_user_schedule_with_additional_shifts(
                user.fullname, current_month_name, user.division
            )
        )

        # Calculate actual working hours from schedule with holiday detection
        total_working_hours = 0
        working_days = 0
        holiday_hours = 0
        holiday_days_worked = []
        night_hours = 0
        night_holiday_hours = 0

        # Additional shift tracking
        additional_shift_hours = 0
        additional_shift_holiday_hours = 0
        additional_shift_days_worked = []
        additional_shift_night_hours = 0
        additional_shift_night_holiday_hours = 0

        # Process regular schedule
        for day, schedule_time in schedule_data.items():
            if schedule_time and schedule_time not in ["Не указано", "В", "О"]:
                # Parse time format like "08:00-17:00"
                import re

                time_match = re.search(
                    r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", schedule_time
                )
                if time_match:
                    start_hour, start_min, end_hour, end_min = map(
                        int, time_match.groups()
                    )
                    start_minutes = start_hour * 60 + start_min
                    end_minutes = end_hour * 60 + end_min

                    # Handle overnight shifts
                    if end_minutes < start_minutes:
                        end_minutes += 24 * 60

                    day_hours = (end_minutes - start_minutes) / 60

                    # Calculate night hours for this shift
                    shift_night_hours = calculate_night_hours(
                        start_hour, start_min, end_hour, end_min
                    )

                    # For 12-hour shifts, subtract 1 hour for lunch break
                    if day_hours == 12:
                        day_hours = 11
                        # Adjust night hours proportionally if lunch break affects them
                        if shift_night_hours > 0:
                            shift_night_hours = shift_night_hours * (11 / 12)

                    # Check if this day is a holiday
                    try:
                        work_date = datetime.date(now.year, now.month, int(day))
                        is_holiday = await production_calendar.is_holiday(work_date)
                        holiday_name = await production_calendar.get_holiday_name(
                            work_date
                        )

                        if is_holiday and holiday_name:
                            holiday_hours += day_hours
                            night_holiday_hours += shift_night_hours
                            holiday_days_worked.append(
                                f"{day} - {holiday_name} (+{day_hours:.0f}ч)"
                            )
                        else:
                            night_hours += shift_night_hours
                    except (ValueError, Exception):
                        # Ignore date parsing errors or API failures
                        night_hours += shift_night_hours

                    total_working_hours += day_hours
                    working_days += 1

        # Process additional shifts
        for day, schedule_time in additional_shifts_data.items():
            if schedule_time and schedule_time not in ["Не указано", "В", "О"]:
                # Parse time format like "08:00-17:00"
                import re

                time_match = re.search(
                    r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", schedule_time
                )
                if time_match:
                    start_hour, start_min, end_hour, end_min = map(
                        int, time_match.groups()
                    )
                    start_minutes = start_hour * 60 + start_min
                    end_minutes = end_hour * 60 + end_min

                    # Handle overnight shifts
                    if end_minutes < start_minutes:
                        end_minutes += 24 * 60

                    day_hours = (end_minutes - start_minutes) / 60

                    # Calculate night hours for this additional shift
                    shift_night_hours = calculate_night_hours(
                        start_hour, start_min, end_hour, end_min
                    )

                    # For 12-hour shifts, subtract 1 hour for lunch break
                    if day_hours == 12:
                        day_hours = 11
                        # Adjust night hours proportionally if lunch break affects them
                        if shift_night_hours > 0:
                            shift_night_hours = shift_night_hours * (11 / 12)

                    # Check if this day is a holiday
                    try:
                        work_date = datetime.date(now.year, now.month, int(day))
                        is_holiday = await production_calendar.is_holiday(work_date)
                        holiday_name = await production_calendar.get_holiday_name(
                            work_date
                        )

                        if is_holiday and holiday_name:
                            additional_shift_holiday_hours += day_hours
                            additional_shift_night_holiday_hours += shift_night_hours
                            additional_shift_days_worked.append(
                                f"{day} - {holiday_name} (+{day_hours:.0f}ч доп.)"
                            )
                        else:
                            additional_shift_night_hours += shift_night_hours
                            additional_shift_days_worked.append(
                                f"{day} - Доп. смена (+{day_hours:.0f}ч)"
                            )
                    except (ValueError, Exception):
                        # Ignore date parsing errors or API failures
                        additional_shift_night_hours += shift_night_hours
                        additional_shift_days_worked.append(
                            f"{day} - Доп. смена (+{day_hours:.0f}ч)"
                        )

                    additional_shift_hours += day_hours

    except Exception as e:
        raise Exception(f"Произошла ошибка при расчете: {e}")

    # Calculate salary components with holiday x2 multiplier, night hours x1.2, and additional shifts
    # Separate regular and night hours
    regular_hours = (
        total_working_hours - holiday_hours - night_hours - night_holiday_hours
    )
    regular_additional_shift_hours = (
        additional_shift_hours
        - additional_shift_holiday_hours
        - additional_shift_night_hours
        - additional_shift_night_holiday_hours
    )

    # Base salary calculation
    base_salary = (
        (regular_hours * pay_rate)
        + (holiday_hours * pay_rate * 2)
        + (night_hours * pay_rate * 1.2)
        + (night_holiday_hours * pay_rate * 2.4)
    )

    # Additional shifts calculation: (pay_rate * 2) + (pay_rate * 0.63) per hour
    additional_shift_rate = (pay_rate * 2) + (pay_rate * 0.63)
    additional_shift_holiday_rate = additional_shift_rate * 2  # Double for holidays
    additional_shift_night_rate = additional_shift_rate * 1.2  # Night multiplier
    additional_shift_night_holiday_rate = additional_shift_rate * 2.4  # Night + holiday

    additional_shift_salary = (
        (regular_additional_shift_hours * additional_shift_rate)
        + (additional_shift_holiday_hours * additional_shift_holiday_rate)
        + (additional_shift_night_hours * additional_shift_night_rate)
        + (additional_shift_night_holiday_hours * additional_shift_night_holiday_rate)
    )

    # Calculate individual KPI premium amounts (based only on base salary, not additional shifts)
    csi_premium_amount = base_salary * ((user_premium.csi_premium or 0) / 100)
    flr_premium_amount = base_salary * ((user_premium.flr_premium or 0) / 100)
    gok_premium_amount = base_salary * ((user_premium.gok_premium or 0) / 100)
    target_premium_amount = base_salary * ((user_premium.target_premium or 0) / 100)
    discipline_premium_amount = base_salary * (
        (user_premium.discipline_premium or 0) / 100
    )
    tests_premium_amount = base_salary * ((user_premium.tests_premium or 0) / 100)
    thanks_premium_amount = base_salary * ((user_premium.thanks_premium or 0) / 100)
    tutors_premium_amount = base_salary * ((user_premium.tutors_premium or 0) / 100)
    head_adjust_premium_amount = base_salary * (
        (user_premium.head_adjust_premium or 0) / 100
    )

    premium_multiplier = (user_premium.total_premium or 0) / 100
    premium_amount = base_salary * premium_multiplier
    total_salary = base_salary + premium_amount + additional_shift_salary

    message_text = f"""💰 <b>Расчет зарплаты</b>

📅 <b>Период:</b> {current_month_name} {now.year}

⏰ <b>Рабочие часы:</b>
<blockquote>Рабочих дней: {working_days}
Всего часов: {round(total_working_hours)}{
        f'''

🎉 Праздничные дни (x2): {round(holiday_hours)}ч
{chr(10).join(holiday_days_worked)}'''
        if holiday_days_worked
        else ""
    }{
        f'''

⭐ Доп. смены: {round(additional_shift_hours)}ч
{chr(10).join(additional_shift_days_worked)}'''
        if additional_shift_days_worked
        else ""
    }</blockquote>

💵 <b>Оклад:</b>
<blockquote>Ставка в час: {format_value(pay_rate, " ₽")}

{
        chr(10).join(
            [
                line
                for line in [
                    f"Обычные часы: {round(regular_hours)}ч × {pay_rate}₽ = {round(regular_hours * pay_rate)}₽"
                    if regular_hours > 0
                    else None,
                    f"Ночные часы: {round(night_hours)}ч × {round(pay_rate * 1.2, 2)}₽ = {round(night_hours * pay_rate * 1.2)}₽"
                    if night_hours > 0
                    else None,
                    f"Праздничные часы: {round(holiday_hours)}ч × {pay_rate * 2}₽ = {round(holiday_hours * pay_rate * 2)}₽"
                    if holiday_hours > 0
                    else None,
                    f"Ночные праздничные часы: {round(night_holiday_hours)}ч × {round(pay_rate * 2.4, 2)}₽ = {round(night_holiday_hours * pay_rate * 2.4)}₽"
                    if night_holiday_hours > 0
                    else None,
                ]
                if line is not None
            ]
        )
    }

Сумма оклада: {format_value(round(base_salary), " ₽")}</blockquote>{
        f'''

⭐ <b>Доп. смены:</b>
<blockquote>{
            chr(10).join([
                line for line in [
                    f"Обычные доп. смены: {round(regular_additional_shift_hours)}ч × {additional_shift_rate:.2f}₽ = {round(regular_additional_shift_hours * additional_shift_rate)}₽"
                    if regular_additional_shift_hours > 0 else None,
                    f"Ночные доп. смены: {round(additional_shift_night_hours)}ч × {additional_shift_night_rate:.2f}₽ = {round(additional_shift_night_hours * additional_shift_night_rate)}₽"
                    if additional_shift_night_hours > 0 else None,
                    f"Праздничные доп. смены: {round(additional_shift_holiday_hours)}ч × {additional_shift_holiday_rate:.2f}₽ = {round(additional_shift_holiday_hours * additional_shift_holiday_rate)}₽"
                    if additional_shift_holiday_hours > 0 else None,
                    f"Ночные праздничные доп. смены: {round(additional_shift_night_holiday_hours)}ч × {additional_shift_night_holiday_rate:.2f}₽ = {round(additional_shift_night_holiday_hours * additional_shift_night_holiday_rate)}₽"
                    if additional_shift_night_holiday_hours > 0 else None
                ] if line is not None
            ])
        }

Сумма доп. смен: {format_value(round(additional_shift_salary), " ₽")}</blockquote>'''
        if additional_shift_salary > 0 else ""
    }

🎁 <b>Премия:</b>
<blockquote expandable>Общий процент премии: {
        format_percentage(user_premium.total_premium)
    }
Общая сумма премии: {format_value(round(premium_amount), " ₽")}
Стоимость 1% премии: ~{
        round(premium_amount / user_premium.total_premium)
        if user_premium.total_premium and user_premium.total_premium > 0
        else 0
    } ₽

🌟 Показатели:
Оценка: {format_percentage(user_premium.csi_premium)} = {
        format_value(round(csi_premium_amount), " ₽")
    }
FLR: {format_percentage(user_premium.flr_premium)} = {
        format_value(round(flr_premium_amount), " ₽")
    }
ГОК: {format_percentage(user_premium.gok_premium)} = {
        format_value(round(gok_premium_amount), " ₽")
    }
Цель: {format_percentage(user_premium.target_premium)} = {
        format_value(round(target_premium_amount), " ₽")
    }

💼 Дополнительно:
Дисциплина: {format_percentage(user_premium.discipline_premium)} = {
        format_value(round(discipline_premium_amount), " ₽")
    }
Тестирование: {format_percentage(user_premium.tests_premium)} = {
        format_value(round(tests_premium_amount), " ₽")
    }
Благодарности: {format_percentage(user_premium.thanks_premium)} = {
        format_value(round(thanks_premium_amount), " ₽")
    }
Наставничество: {format_percentage(user_premium.tutors_premium)} = {
        format_value(round(tutors_premium_amount), " ₽")
    }
Ручная правка: {format_percentage(user_premium.head_adjust_premium)} = {
        format_value(round(head_adjust_premium_amount), " ₽")
    }</blockquote>

💰 <b>Итого к выплате:</b>
~<b>{format_value(round(total_salary, 1), " ₽")}</b>

<blockquote expandable>⚠️ <b>Важное</b>

Расчет представляет <b>примерную</b> сумму после вычета НДФЛ
Районный коэффициент <b>не участвует в расчете</b>, т.к. примерно покрывает НДФЛ

🧪 <b>Формулы</b>
Обычные часы: часы × ставка
Праздничные часы: часы × ставка × 2
Ночные часы: часы × ставка × 1.2
Ночные праздничные часы: часы × ставка × 2.4
Доп. смены: часы × (ставка × 2.63)

Ночными часами считается локальное время 22:00 - 6:00
Праздничные дни считаются по производственному <a href='https://www.consultant.ru/law/ref/calendar/proizvodstvennye/'>календарю</a></blockquote>

<i>Расчет от: {now.strftime("%d.%m.%y %H:%M")}</i>
<i>Данные премии от: {
        user_premium.updated_at.replace(tzinfo=datetime.timezone.utc)
        .astimezone(datetime.timezone(datetime.timedelta(hours=5)))
        .strftime("%d.%m.%y %H:%M")
        if user_premium.updated_at
        else "—"
    }</i>"""

    try:
        await callback.message.edit_text(
            message_text, reply_markup=kpi_salary_kb(), disable_web_page_preview=True
        )
    except TelegramBadRequest:
        await callback.answer("Обновлений нет")
