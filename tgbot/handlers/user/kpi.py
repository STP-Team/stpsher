import datetime

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from infrastructure.database.models import Employee
from infrastructure.database.repo.KPI.requests import KPIRequestsRepo
from tgbot.keyboards.user.kpi import kpi_kb
from tgbot.keyboards.user.main import MainMenu

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
<blockquote>Текущий: {format_value(premium.csi)}
Норматив: {format_value(premium.csi_normative)}  
Выполнение: {format_percentage(premium.csi_normative_rate)}</blockquote>

🎯 <b>Отклик</b>
<blockquote>Текущий: {format_value(premium.csi_response)}
Норматив: {format_value(premium.csi_response_normative)}
Выполнение: {format_percentage(premium.csi_response_rate)}</blockquote>

🔧 <b>FLR - {format_percentage(premium.flr_premium)}</b>
<blockquote>Текущий: {format_value(premium.flr)}
Норматив: {format_value(premium.flr_normative)}
Выполнение: {format_percentage(premium.flr_normative_rate)}</blockquote>

⚖️ <b>ГОК - {format_percentage(premium.gok_premium)}</b>
<blockquote>Текущий: {format_value(premium.gok)}
Норматив: {format_value(premium.gok_normative)}
Выполнение: {format_percentage(premium.gok_normative_rate)}</blockquote>

🎯 <b>Цель - {format_percentage(premium.target_premium)}</b>
<blockquote>Тип: {premium.target_type or "—"}
Факт: {format_value(premium.target)}
План: {format_value(premium.target_goal_first)} / {format_value(premium.target_goal_second)}
Выполнение: {format_percentage(premium.target_result_first)} / {format_percentage(premium.target_result_second)}</blockquote>

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
