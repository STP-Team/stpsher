"""Запуск диалога для специалистов."""

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from stp_database.models.STP import Employee

from tgbot.dialogs.states.admin import AdminSG
from tgbot.dialogs.states.gok import GokSG
from tgbot.dialogs.states.head import HeadSG
from tgbot.dialogs.states.mip import MipSG
from tgbot.dialogs.states.root import RootSG
from tgbot.dialogs.states.user import UserSG
from tgbot.keyboards.auth import auth_kb
from tgbot.services.event_logger import EventLogger

logger = logging.getLogger(__name__)

start_router = Router()
start_router.message.filter(F.chat.type == "private")
start_router.callback_query.filter(F.message.chat.type == "private")


@start_router.message(CommandStart())
async def start(
    message: Message,
    user: Employee,
    dialog_manager: DialogManager,
    event_logger: EventLogger | None,
) -> None:
    """Запуск/сброс состояния диалога.

    Запускает авторизацию в случае ее отсутствия у пользователя.

    Args:
        message: Сообщение пользователя
        user: Экземпляр пользователя с моделью Employee
        dialog_manager: Менеджер диалога
        event_logger: Логгер событий
    """
    if not user:
        await message.answer(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    if event_logger:
        await event_logger.log_bot_start(user.user_id)

    role_menu_mapping = {
        "1": UserSG.menu,
        "2": HeadSG.menu,
        "3": UserSG.menu,
        "4": AdminSG.menu,
        "5": GokSG.menu,
        "6": MipSG.menu,
        "10": RootSG.menu,
    }

    menu_state = role_menu_mapping.get(str(user.role), UserSG.menu)
    await dialog_manager.start(menu_state, mode=StartMode.RESET_STACK)
