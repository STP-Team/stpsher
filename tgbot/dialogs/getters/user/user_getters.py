import datetime

from infrastructure.database.models import Employee
from infrastructure.database.repo.KPI.requests import KPIRequestsRepo
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.dialogs.getters.common.db_getters import db_getter
from tgbot.services.leveling import LevelingSystem
from tgbot.services.salary import SalaryFormatter


async def kpi_getter(**kwargs):
    base_data = await db_getter(**kwargs)
    user: Employee = base_data.get("user")
    kpi_repo: KPIRequestsRepo = base_data.get("kpi_repo")

    premium = None
    if base_data:
        premium = await kpi_repo.spec_premium.get_premium(fullname=user.fullname)

    if not premium:
        return {
            **base_data,
            "kpi_text": "🌟 <b>Показатели</b>\n\nНе смог найти твои показатели в премиуме :(",
        }

    # Format dates
    updated_at_str = "—"
    if premium.updated_at:
        updated_at_str = (
            premium.updated_at.replace(tzinfo=datetime.timezone.utc)
            .astimezone(datetime.timezone(datetime.timedelta(hours=5)))
            .strftime("%d.%m.%y %H:%M")
        )

    current_time_str = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=5))
    ).strftime("%d.%m.%y %H:%M")

    # Conditional contact type text
    contacts_text = (
        f"📈 Всего чатов: {SalaryFormatter.format_value(premium.contacts_count)}"
        if user.division == "НЦК"
        else f"📈 Всего звонков: {SalaryFormatter.format_value(premium.contacts_count)}"
    )

    delay_text = (
        f"⏰ Задержка: {SalaryFormatter.format_value(premium.delay, ' сек')}"
        if user.division != "НЦК"
        else ""
    )

    kpi_text = f"""🌟 <b>Показатели</b>

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

{contacts_text}
{delay_text}
<i>Выгружено: {updated_at_str}</i>
<i>Обновлено: {current_time_str}</i>"""

    return {**base_data, "kpi_text": kpi_text}


async def game_getter(**kwargs):
    base_data = await db_getter(**kwargs)
    stp_repo: MainRequestsRepo = base_data.get("stp_repo")
    user: Employee = base_data.get("user")

    user_balance = await stp_repo.transaction.get_user_balance(user_id=user.user_id)
    achievements_sum = await stp_repo.transaction.get_user_achievements_sum(
        user_id=user.user_id
    )
    purchases_sum = await stp_repo.purchase.get_user_purchases_sum(user_id=user.user_id)
    level_info = LevelingSystem.get_level_info_text(achievements_sum, user_balance)

    return {
        **base_data,
        "achievements_sum": achievements_sum,
        "purchases_sum": purchases_sum,
        "level_info": level_info,
    }
