# tgbot/handlers/user/schedule/main.py (новый файл)

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import Employee
from tgbot.handlers.user.schedule.main import schedule_service
from tgbot.keyboards.user.schedule.main import (
    GroupNavigation,
    ScheduleMenu,
    get_yekaterinburg_date,
    group_schedule_kb,
)
from tgbot.services.schedule.parsers import GroupScheduleParser

logger = logging.getLogger(__name__)

user_schedule_group_router = Router()
user_schedule_group_router.message.filter(F.chat.type == "private")
user_schedule_group_router.callback_query.filter(F.message.chat.type == "private")


class GroupScheduleService:
    """Сервис для работы с групповым расписанием"""

    def __init__(self):
        self.group_parser = GroupScheduleParser()

    async def get_group_schedule_for_user(
        self, user: Employee, date: datetime, page: int, stp_repo
    ) -> tuple[str, int, bool, bool]:
        """Получить групповое расписание для обычного пользователя"""
        try:
            # Получаем коллег по группе
            group_members = await self.group_parser.get_group_members_for_user(
                user.fullname, date, user.division, stp_repo
            )

            # Форматируем расписание с пагинацией
            return self.group_parser.format_group_schedule_for_user(
                date, group_members, page
            )

        except Exception as e:
            logger.error(
                f"Ошибка получения группового расписания для {user.fullname}: {e}"
            )
            return "❌ Ошибка получения расписания группы", 1, False, False


# Создаем экземпляр сервиса
group_schedule_service = GroupScheduleService()


@user_schedule_group_router.callback_query(ScheduleMenu.filter(F.menu == "group"))
async def group_schedule(callback: CallbackQuery, user: Employee, stp_repo):
    """Обработчик группового расписания для пользователя"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    try:
        current_date = get_yekaterinburg_date()

        # Получаем групповое расписание
        (
            text,
            total_pages,
            has_prev,
            has_next,
        ) = await group_schedule_service.get_group_schedule_for_user(
            user, current_date, 1, stp_repo
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=group_schedule_kb(
                current_date=current_date,
                page=1,
                total_pages=total_pages,
                has_prev=has_prev,
                has_next=has_next,
                user_type="user",
                from_group_mgmt=False,
            ),
        )

    except Exception as e:
        await schedule_service.handle_schedule_error(callback, e)


@user_schedule_group_router.callback_query(
    GroupNavigation.filter(F.user_type == "user")
)
async def handle_group_navigation(
    callback: CallbackQuery, callback_data: GroupNavigation, user: Employee, stp_repo
):
    """Обработчик навигации по групповому расписанию"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    try:
        action = callback_data.action
        page = callback_data.page
        user_type = callback_data.user_type

        if action == "-":
            await callback.answer()
            return

        # Определяем целевую дату
        if action == "today":
            target_date = get_yekaterinburg_date()
        elif action in ["prev", "next"]:
            target_date = schedule_service.parse_date_from_callback(callback_data.date)
        else:  # prev_page, next_page
            target_date = schedule_service.parse_date_from_callback(callback_data.date)

        # Получаем данные группового расписания
        (
            text,
            total_pages,
            has_prev,
            has_next,
        ) = await group_schedule_service.get_group_schedule_for_user(
            user, target_date, page, stp_repo
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=group_schedule_kb(
                current_date=target_date,
                page=page,
                total_pages=total_pages,
                has_prev=has_prev,
                has_next=has_next,
                user_type=user_type,
                from_group_mgmt=callback_data.from_group_mgmt,
            ),
        )
        await callback.answer()

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)
