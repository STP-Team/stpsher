"""Запуск диалога для специалистов."""

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import NoContextError
from stp_database import Employee

from tgbot.dialogs.states.user import UserSG
from tgbot.keyboards.auth import auth_kb
from tgbot.services.event_logger import EventLogger

logger = logging.getLogger(__name__)

user_router = Router()
user_router.message.filter(F.chat.type == "private")
user_router.callback_query.filter(F.message.chat.type == "private")


@user_router.message(CommandStart())
async def user_start(
    message: Message,
    user: Employee,
    dialog_manager: DialogManager,
    event_logger: EventLogger | None,
) -> None:
    """Запуск/сброс состояния диалога для специалистов и дежурных.

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

    try:
        await dialog_manager.done()
    except NoContextError:
        pass

    await dialog_manager.start(UserSG.menu, mode=StartMode.RESET_STACK)
