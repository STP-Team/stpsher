from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import Employee
from infrastructure.database.models.KPI.rg_month_stats import HeadMonthKPI
from infrastructure.database.repo.KPI.requests import KPIRequestsRepo
from tgbot.filters.role import HeadFilter
from tgbot.keyboards.head.kpi import kpi_kb
from tgbot.keyboards.user.main import MainMenu
from tgbot.misc.dicts import russian_months

head_kpi_router = Router()
head_kpi_router.message.filter(F.chat.type == "private", HeadFilter())
head_kpi_router.callback_query.filter(F.message.chat.type == "private", HeadFilter())


@head_kpi_router.callback_query(MainMenu.filter(F.menu == "kpi"))
async def head_start_cb(
    callback: CallbackQuery, user: Employee, kpi_repo: KPIRequestsRepo
):
    head_kpi: HeadMonthKPI = await kpi_repo.head_month_kpi.get_kpi(
        fullname=user.fullname
    )

    contact_type = "чатов" if user.division == "НЦК" else "звонков"

    # Текст для обоих направлений
    message_text = f"""<b>🌟 Показатели группы • {russian_months.get(head_kpi.updated_at.month).capitalize()}</b>

<b>📊 Всего {contact_type}:</b> {head_kpi.contacts_count}

⚡️ <b>AHT:</b> {head_kpi.aht if head_kpi.aht else "Неизвестно"}
🛠️ <b>FLR:</b> {head_kpi.flr if head_kpi.flr else "Неизвестно"}  
⚖️ <b>ГОК:</b> {head_kpi.gok if head_kpi.gok else "Неизвестно"}
🥇 <b>Оценка:</b> {head_kpi.csi if head_kpi.csi else "Неизвестно"}
🥱 <b>Отклик:</b> {head_kpi.pok if head_kpi.pok else "Неизвестно"}"""

    # Текст для НТП
    if user.division != "НЦК":
        message_text += f"\n⏳ <b>Задержка:</b> {head_kpi.delay if head_kpi.delay else 'Неизвестно'}"
        message_text += (
            f"\n<b>Продажи:</b> {head_kpi.sales_count if head_kpi.sales_count else '0'}"
        )

    message_text += f"""

<i>Время обновления: {head_kpi.updated_at.strftime("%H:%M:%S %d.%m.%y")}</i>
<i>Показатели обновляются каждый день в ~10:00 ПРМ</i>"""

    await callback.message.edit_text(
        message_text,
        reply_markup=kpi_kb(),
    )
