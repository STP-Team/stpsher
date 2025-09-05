from aiogram import F, Router
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
    day_kpi = await kpi_repo.spec_day_kpi.get_kpi(fullname=user.fullname)

    contact_type = "чатов" if user.division == "НЦК" else "звонков"

    await callback.message.edit_text(
        f"""🚧 Функционал KPI ограничен

<b>📊 Всего {contact_type}:</b> {day_kpi.contacts_count}

⚡️ <b>AHT:</b> {day_kpi.aht if day_kpi.aht else "Неизвестно"}
🛠️ <b>FLR:</b> {day_kpi.flr if day_kpi.flr else "Неизвестно"}
🥇 <b>Оценка:</b> {day_kpi.csi if day_kpi.csi else "Неизвестно"}
🥱 <b>Отклик:</b> {day_kpi.pok if day_kpi.pok else "Неизвестно"}""",
        reply_markup=kpi_kb(),
    )
