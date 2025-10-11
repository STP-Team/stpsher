import datetime

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from stp_database import Employee
from stp_database.repo.KPI.requests import KPIRequestsRepo

from tgbot.filters.role import HeadFilter
from tgbot.keyboards.head.kpi import kpi_calculator_kb, kpi_kb, kpi_salary_kb
from tgbot.keyboards.user.main import MainMenu
from tgbot.services.salary import KPICalculator, SalaryCalculator, SalaryFormatter

head_kpi_router = Router()
head_kpi_router.message.filter(F.chat.type == "private", HeadFilter())
head_kpi_router.callback_query.filter(F.message.chat.type == "private", HeadFilter())


@head_kpi_router.callback_query(MainMenu.filter(F.menu == "kpi"))
async def head_start_cb(
    callback: CallbackQuery, user: Employee, kpi_repo: KPIRequestsRepo
):
    premium = await kpi_repo.head_premium.get_premium(fullname=user.fullname)
    if premium is None:
        await callback.message.edit_text(
            """🌟 <b>Показатели</b>

Не смог найти твои показатели в премиуме :(""",
            reply_markup=kpi_kb(),
        )
        return

    message_text = f"""🌟 <b>Показатели</b>

🔧 <b>FLR - {SalaryFormatter.format_percentage(premium.flr_premium)}</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.flr)}
План: {SalaryFormatter.format_value(premium.flr_normative)}</blockquote>

⚖️ <b>ГОК - {SalaryFormatter.format_percentage(premium.gok_premium)}</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.gok)}
План: {SalaryFormatter.format_value(premium.gok_normative)}</blockquote>

🎯 <b>Цель - {SalaryFormatter.format_percentage(premium.target_premium)}</b>
<blockquote>Тип: {premium.target_type or "—"}
Факт: {SalaryFormatter.format_value(premium.target)}
План: {SalaryFormatter.format_value(round(premium.target_normative_first))} / {SalaryFormatter.format_value(round(premium.target_normative_second))}</blockquote>

💰 <b>Итого:</b>
<b>Общая премия: {SalaryFormatter.format_percentage(premium.total_premium)}</b>

{"📈 Всего чатов: " + SalaryFormatter.format_value(premium.contacts_count) if user.division == "НЦК" else "📈 Всего звонков: " + SalaryFormatter.format_value(premium.contacts_count)}

<i>Выгружено: {premium.updated_at.replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=5))).strftime("%d.%m.%y %H:%M") if premium.updated_at else "—"}</i>
<i>Обновлено: {datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5))).strftime("%d.%m.%y %H:%M")}</i>"""

    try:
        await callback.message.edit_text(message_text, reply_markup=kpi_kb())
    except TelegramBadRequest:
        await callback.answer("Обновлений нет")


@head_kpi_router.callback_query(MainMenu.filter(F.menu == "kpi_calculator"))
async def head_kpi_calculator_cb(
    callback: CallbackQuery, user: Employee, kpi_repo: KPIRequestsRepo
):
    user_premium = await kpi_repo.head_premium.get_premium(fullname=user.fullname)

    if user_premium is None:
        await callback.message.edit_text(
            """🧮 <b>Калькулятор KPI</b>

Не смог найти твои показатели в премиуме :(""",
            reply_markup=kpi_calculator_kb(),
        )
        return

    flr_calculation = KPICalculator.calculate_flr_needed(
        user.division, user_premium.flr, user_premium.flr_normative, is_head=True
    )
    gok_calculation = KPICalculator.calculate_gok_needed(
        user.division, user_premium.gok, user_premium.gok_normative, is_head=True
    )
    target_calculation = KPICalculator.calculate_target_needed(
        user_premium.target,
        user_premium.target_normative_first,
        user_premium.target_normative_second,
        user_premium.target_type,
        is_head=True,
    )

    message_text = f"""🧮 <b>Калькулятор KPI</b>

🔧 <b>FLR</b>
<blockquote>Текущий: {SalaryFormatter.format_value(user_premium.flr)} ({SalaryFormatter.format_percentage(user_premium.flr_normative_rate)})
План: {SalaryFormatter.format_value(user_premium.flr_normative)}

<b>Для премии:</b>
{flr_calculation}</blockquote>

⚖️ <b>ГОК</b>
<blockquote>Текущий: {SalaryFormatter.format_value(round(user_premium.gok))} ({SalaryFormatter.format_percentage(user_premium.gok_normative_rate)})
План: {SalaryFormatter.format_value(round(user_premium.gok_normative))}

<b>Для премии:</b>
{gok_calculation}</blockquote>

🎯 <b>Цель</b>
<blockquote>Факт: {SalaryFormatter.format_value(user_premium.target)} ({SalaryFormatter.format_percentage(user_premium.target_result_first)} / {SalaryFormatter.format_percentage(user_premium.target_result_second)})
План: {SalaryFormatter.format_value(round(user_premium.target_normative_first))} / {SalaryFormatter.format_value(round(user_premium.target_normative_second))}

<b>Для премии:</b>
{target_calculation}</blockquote>

<i>Данные от: {user_premium.updated_at.replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=5))).strftime("%d.%m.%y %H:%M") if user_premium.updated_at else "—"}</i>"""
    try:
        await callback.message.edit_text(message_text, reply_markup=kpi_calculator_kb())
    except TelegramBadRequest:
        await callback.answer("Обновлений нет")


@head_kpi_router.callback_query(MainMenu.filter(F.menu == "kpi_salary"))
async def head_kpi_salary_cb(
    callback: CallbackQuery, user: Employee, kpi_repo: KPIRequestsRepo
):
    user_premium = await kpi_repo.head_premium.get_premium(fullname=user.fullname)

    if user_premium is None:
        await callback.message.edit_text(
            """💰 <b>Расчет зарплаты</b>

Не смог найти твои показатели в премиуме :(""",
            reply_markup=kpi_salary_kb(),
        )
        return

    try:
        salary_result = await SalaryCalculator.calculate_salary(
            user=user, premium_data=user_premium
        )

        message_text = SalaryFormatter.format_salary_message(
            salary_result, user_premium
        )
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
