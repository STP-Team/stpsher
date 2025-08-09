import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from tgbot.keyboards.user.main import MainMenu, auth_kb
from tgbot.keyboards.user.schedule.main import (
    MonthNavigation,
    ScheduleMenu,
    create_detailed_schedule_keyboard,
    schedule_kb,
    schedule_with_month_kb,
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
            compact=True,  # По умолчанию короткий режим
        )

        await callback.message.edit_text(
            text=schedule,
            reply_markup=schedule_with_month_kb(
                current_month=month, schedule_type="my"
            ),
        )

    except Exception as e:
        await callback.message.edit_text(
            text=f"❌ Ошибка при получении расписания:\n<code>{e}</code>",
            reply_markup=schedule_kb(),
        )


@user_schedule_router.callback_query(MonthNavigation.filter(F.action == "compact"))
async def handle_compact_view(callback: CallbackQuery, user: User):
    """Обработчик перехода к компактному виду"""
    if not user:
        await callback.message.answer(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    callback_data = MonthNavigation.unpack(callback.data)
    current_month = callback_data.current_month
    user_type = callback_data.schedule_type

    try:
        # Показываем расписание в компактном режиме
        schedule = get_user_schedule_formatted(
            fullname=user.fullname,
            month=current_month,
            compact=True,
        )

        await callback.message.edit_text(
            text=schedule,
            reply_markup=schedule_with_month_kb(
                current_month=current_month, schedule_type=user_type
            ),
        )

        await callback.answer()

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@user_schedule_router.callback_query(MonthNavigation.filter())
async def handle_month_navigation(
    callback: CallbackQuery, callback_data: MonthNavigation, user: User
):
    """Обработчик навигации по месяцам"""
    if not user:
        await callback.message.answer(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    # Извлекаем данные из callback
    action = callback_data.action
    current_month = callback_data.current_month
    schedule_type = callback_data.schedule_type

    try:
        if action in ["prev", "next"]:
            # Показываем расписание в компактном режиме
            schedule = get_user_schedule_formatted(
                fullname=user.fullname,
                month=current_month,
                compact=True,
            )

            await callback.message.edit_text(
                text=schedule,
                reply_markup=schedule_with_month_kb(
                    current_month=current_month, schedule_type=schedule_type
                ),
            )

        elif action == "detailed":
            # Показываем детальное расписание
            schedule = get_user_schedule_formatted(
                fullname=user.fullname,
                month=current_month,
                compact=False,  # Детальный режим
            )

            # Создаем клавиатуру с кнопкой "Кратко"
            keyboard = create_detailed_schedule_keyboard(current_month, schedule_type)

            await callback.message.edit_text(
                text=schedule,
                reply_markup=keyboard,
            )

        await callback.answer()

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)
