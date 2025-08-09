import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from tgbot.keyboards.user.main import MainMenu, auth_kb
from tgbot.keyboards.user.schedule.main import (
    schedule_kb,
    schedule_with_month_kb,
    ScheduleMenu,
)
from tgbot.misc.dicts import russian_months
from tgbot.services.sheets import get_user_schedule_formatted

user_schedule_router = Router()
user_schedule_router.message.filter(F.chat.type == "private")
user_schedule_router.callback_query.filter(F.message.chat.type == "private")


@user_schedule_router.callback_query(MainMenu.filter(F.menu == "schedule"))
async def schedule(callback: CallbackQuery, user: User):
    if not user:
        await callback.message.answer(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    await callback.message.edit_text(
        """📅 Меню графиков

Используй меню для выбора действия""",
        reply_markup=schedule_kb(),
    )


@user_schedule_router.callback_query(ScheduleMenu.filter(F.menu == "my"))
async def user_schedule(callback: CallbackQuery, user: User):
    if not user:
        await callback.message.answer(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    try:
        month = russian_months[datetime.datetime.now().month]

        schedule = get_user_schedule_formatted(
            fullname=user.fullname,
            month=month,
            compact=True,
        )

        await callback.message.edit_text(
            text=schedule,
            reply_markup=schedule_with_month_kb(current_month=month, user_type="my"),
            parse_mode="HTML",
        )

    except Exception as e:
        await callback.message.edit_text(
            text=f"❌ Ошибка при получении расписания:\n<code>{e}</code>",
            reply_markup=schedule_kb(),
            parse_mode="HTML",
        )
