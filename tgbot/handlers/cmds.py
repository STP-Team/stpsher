"""Запуск диалога для специалистов."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from stp_database.models.STP import Employee

from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.dialogs.states.common.game import GameSG
from tgbot.dialogs.states.common.kpi import KpiSG
from tgbot.dialogs.states.common.schedule import Schedules
from tgbot.dialogs.states.common.search import SearchSG
from tgbot.keyboards.auth import auth_kb
from tgbot.services.event_logger import EventLogger

logger = logging.getLogger(__name__)

cmds_router = Router()
cmds_router.message.filter(F.chat.type == "private")
cmds_router.callback_query.filter(F.message.chat.type == "private")


@cmds_router.message(Command("schedule"))
async def schedule_cmd(
    message: Message,
    user: Employee,
    dialog_manager: DialogManager,
    event_logger: EventLogger | None,
) -> None:
    """Запуск диалога графика пользователя.

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

    await dialog_manager.start(Schedules.my, mode=StartMode.RESET_STACK)


@cmds_router.message(Command("exchanges"))
async def exchanges_cmd(
    message: Message,
    user: Employee,
    dialog_manager: DialogManager,
    event_logger: EventLogger | None,
) -> None:
    """Запуск диалога подмен.

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

    await dialog_manager.start(Exchanges.menu, mode=StartMode.RESET_STACK)


@cmds_router.message(Command("kpi"))
async def kpi_cmd(
    message: Message,
    user: Employee,
    dialog_manager: DialogManager,
    event_logger: EventLogger | None,
) -> None:
    """Запуск диалога показателей.

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

    await dialog_manager.start(KpiSG.menu, mode=StartMode.RESET_STACK)


@cmds_router.message(Command("salary"))
async def salary_cmd(
    message: Message,
    user: Employee,
    dialog_manager: DialogManager,
    event_logger: EventLogger | None,
) -> None:
    """Запуск диалога зарплаты.

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

    await dialog_manager.start(KpiSG.salary, mode=StartMode.RESET_STACK)


@cmds_router.message(Command("whois"))
async def whois_cmd(
    message: Message,
    user: Employee,
    dialog_manager: DialogManager,
    event_logger: EventLogger | None,
) -> None:
    """Запуск диалога поиска сотрудников.

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

    await dialog_manager.start(SearchSG.query, mode=StartMode.RESET_STACK)


@cmds_router.message(Command("shop"))
async def shop_cmd(
    message: Message,
    user: Employee,
    dialog_manager: DialogManager,
    event_logger: EventLogger | None,
) -> None:
    """Запуск диалога магазина предметов.

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

    await dialog_manager.start(GameSG.products, mode=StartMode.RESET_STACK)
