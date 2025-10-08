import datetime

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from infrastructure.database.models import Employee
from infrastructure.database.repo.KPI.requests import KPIRequestsRepo
from tgbot.keyboards.user.kpi import kpi_calculator_kb, kpi_kb, kpi_salary_kb
from tgbot.keyboards.user.main import MainMenu
from tgbot.services.salary import KPICalculator, SalaryCalculator, SalaryFormatter

user_kpi_router = Router()
user_kpi_router.message.filter(F.chat.type == "private")
user_kpi_router.callback_query.filter(F.message.chat.type == "private")


@user_kpi_router.callback_query(MainMenu.filter(F.menu == "kpi"))
async def user_kpi_cb(
    callback: CallbackQuery, user: Employee, kpi_repo: KPIRequestsRepo
):
    premium = await kpi_repo.spec_premium.get_premium(fullname=user.fullname)

    if (
        premium is None
        or premium.csi_premium is None
        or premium.flr_premium is None
        or premium.gok_premium is None
        or premium.tests_premium is None
        or premium.total_premium is None
    ):
        await callback.message.edit_text(
            """🌟 <b>Показатели</b>

Не смог найти твои показатели в премиуме :(

<i>Вернись позже, когда показатели загрузятся</i>""",
            reply_markup=kpi_kb(),
        )
        return

    message_text = f"""🌟 <b>Показатели</b>

📊 <b>Оценка клиента - {SalaryFormatter.format_percentage(premium.csi_premium)}</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.csi)}
План: {SalaryFormatter.format_value(premium.csi_normative)}  </blockquote>

🎯 <b>Отклик</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.csi_response)}
План: {SalaryFormatter.format_value(round(premium.csi_response_normative))}</blockquote>

🔧 <b>FLR - {SalaryFormatter.format_percentage(premium.flr_premium)}</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.flr)}
План: {SalaryFormatter.format_value(premium.flr_normative)}</blockquote>

⚖️ <b>ГОК - {SalaryFormatter.format_percentage(premium.gok_premium)}</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.gok)}
План: {SalaryFormatter.format_value(premium.gok_normative)}</blockquote>

🎯 <b>Цель - {SalaryFormatter.format_percentage(premium.target_premium)}</b>
<blockquote>Тип: {premium.target_type or "—"}
Факт: {SalaryFormatter.format_value(premium.target)}
План: {SalaryFormatter.format_value(round(premium.target_goal_first))} / {SalaryFormatter.format_value(round(premium.target_goal_second))}</blockquote>

💼 <b>Дополнительно</b>
<blockquote>Дисциплина: {SalaryFormatter.format_percentage(premium.discipline_premium)}
Тестирование: {SalaryFormatter.format_percentage(premium.tests_premium)}
Благодарности: {SalaryFormatter.format_percentage(premium.thanks_premium)}
Наставничество: {SalaryFormatter.format_percentage(premium.tutors_premium)}
Ручная правка: {SalaryFormatter.format_percentage(premium.head_adjust_premium)}</blockquote>

💰 <b>Итого:</b>
<b>Общая премия: {SalaryFormatter.format_percentage(premium.total_premium)}</b>

{"📈 Всего чатов: " + SalaryFormatter.format_value(premium.contacts_count) if user.division == "НЦК" else "📈 Всего звонков: " + SalaryFormatter.format_value(premium.contacts_count)}
{"⏰ Задержка: " + SalaryFormatter.format_value(premium.delay, " сек") if user.division != "НЦК" else ""}
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
    premium = await kpi_repo.spec_premium.get_premium(fullname=user.fullname)

    if (
        premium is None
        or premium.csi_premium is None
        or premium.flr_premium is None
        or premium.gok_premium is None
        or premium.tests_premium is None
        or premium.total_premium is None
    ):
        await callback.message.edit_text(
            """🧮 <b>Калькулятор KPI</b>

Не смог найти твои показатели в премиуме :(

<i>Вернись позже, когда показатели загрузятся</i>""",
            reply_markup=kpi_calculator_kb(),
        )
        return

    csi_calculation = KPICalculator.calculate_csi_needed(
        user.division, premium.csi, premium.csi_normative
    )
    flr_calculation = KPICalculator.calculate_flr_needed(
        user.division, premium.flr, premium.flr_normative
    )
    gok_calculation = KPICalculator.calculate_gok_needed(
        user.division, premium.gok, premium.gok_normative
    )
    target_calculation = KPICalculator.calculate_target_needed(
        premium.target,
        premium.target_goal_first,
        premium.target_goal_second,
        premium.target_type,
    )

    message_text = f"""🧮 <b>Калькулятор KPI</b>

📊 <b>Оценка клиента</b>
<blockquote>Текущий: {SalaryFormatter.format_value(premium.csi)} ({SalaryFormatter.format_percentage(premium.csi_normative_rate)})
План: {SalaryFormatter.format_value(premium.csi_normative)}

<b>Для премии:</b>
{csi_calculation}</blockquote>

🔧 <b>FLR</b>
<blockquote>Текущий: {SalaryFormatter.format_value(premium.flr)} ({SalaryFormatter.format_percentage(premium.flr_normative_rate)})
План: {SalaryFormatter.format_value(premium.flr_normative)}

<b>Для премии:</b>
{flr_calculation}</blockquote>

⚖️ <b>ГОК</b>
<blockquote>Текущий: {SalaryFormatter.format_value(round(premium.gok))} ({SalaryFormatter.format_percentage(premium.gok_normative_rate)})
План: {SalaryFormatter.format_value(round(premium.gok_normative))}

<b>Для премии:</b>
{gok_calculation}</blockquote>

🎯 <b>Цель</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.target)} ({SalaryFormatter.format_percentage(round((premium.target_goal_first / premium.target * 100) if premium.target_type and "AHT" in premium.target_type and premium.target and premium.target > 0 and premium.target_goal_first else (premium.target / premium.target_goal_first * 100) if premium.target_goal_first and premium.target_goal_first > 0 else 0))} / {SalaryFormatter.format_percentage(round((premium.target_goal_second / premium.target * 100) if premium.target_type and "AHT" in premium.target_type and premium.target and premium.target > 0 and premium.target_goal_second else (premium.target / premium.target_goal_second * 100) if premium.target_goal_second and premium.target_goal_second > 0 else 0))})
План: {SalaryFormatter.format_value(round(premium.target_goal_first))} / {SalaryFormatter.format_value(round(premium.target_goal_second))}

Требуется минимум 100 {"чатов" if user.division == "НЦК" else "звонков"} для получения премии за цель

<b>Для премии:</b>
{target_calculation}</blockquote>

<i>Данные от: {premium.updated_at.replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=5))).strftime("%d.%m.%y %H:%M") if premium.updated_at else "—"}</i>"""

    try:
        await callback.message.edit_text(message_text, reply_markup=kpi_calculator_kb())
    except TelegramBadRequest:
        await callback.answer("Обновлений нет")


@user_kpi_router.callback_query(MainMenu.filter(F.menu == "kpi_salary"))
async def user_kpi_salary_cb(
    callback: CallbackQuery, user: Employee, kpi_repo: KPIRequestsRepo
):
    premium = await kpi_repo.spec_premium.get_premium(fullname=user.fullname)

    if (
        premium is None
        or premium.csi_premium is None
        or premium.flr_premium is None
        or premium.gok_premium is None
        or premium.tests_premium is None
        or premium.total_premium is None
    ):
        await callback.message.edit_text(
            """💰 <b>Расчет зарплаты</b>

Не смог найти твои показатели в премиуме :(

<i>Вернись позже, когда показатели загрузятся</i>""",
            reply_markup=kpi_salary_kb(),
        )
        return

    try:
        salary_result = await SalaryCalculator.calculate_salary(
            user=user, premium_data=premium
        )

        # Format the result using centralized formatter
        message_text = SalaryFormatter.format_salary_message(salary_result, premium)
    except Exception as e:
        await callback.message.edit_text(
            f"""💰 <b>Расчет зарплаты</b>

Произошла ошибка при расчете: {e}""",
            reply_markup=kpi_salary_kb(),
        )
        return

    try:
        await callback.message.edit_text(
            message_text, reply_markup=kpi_salary_kb(), disable_web_page_preview=True
        )
    except TelegramBadRequest:
        await callback.answer("Обновлений нет")
