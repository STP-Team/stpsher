import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import ExceptionTypeFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    ErrorEvent,
)
from aiogram_dialog import DialogManager, StartMode, setup_dialogs
from aiogram_dialog.api.exceptions import OutdatedIntent, UnknownIntent, UnknownState
from stp_database import Employee, create_engine, create_session_pool

from tgbot.config import Config, load_config
from tgbot.dialogs.menus import common_dialogs_list, dialogs_list
from tgbot.dialogs.states.admin import AdminSG
from tgbot.dialogs.states.gok import GokSG
from tgbot.dialogs.states.head import HeadSG
from tgbot.dialogs.states.mip import MipSG
from tgbot.dialogs.states.root import RootSG
from tgbot.dialogs.states.user import UserSG
from tgbot.handlers import routers_list
from tgbot.middlewares.ConfigMiddleware import ConfigMiddleware
from tgbot.middlewares.DatabaseMiddleware import DatabaseMiddleware
from tgbot.middlewares.GroupsMiddleware import GroupsMiddleware
from tgbot.middlewares.UsersMiddleware import UsersMiddleware
from tgbot.services.logger import setup_logging
from tgbot.services.schedulers.scheduler import SchedulerManager

bot_config = load_config(".env")

logger = logging.getLogger(__name__)


async def on_startup():
    """Функция, активируемая при запуске основного процесса бота."""
    pass


async def _unknown_intent(error: ErrorEvent, dialog_manager: DialogManager):
    """Обработчик ошибки UnknownIntent - возвращает пользователя в главное меню.

    Args:
        error: Событие ошибки с информацией об исключении и обновлении
        dialog_manager: Менеджер диалога
    """
    logger.warning("Restarting dialog: %s", error.exception)

    # Удаляем старое сообщение без уведомления пользователя
    if error.update.callback_query:
        if error.update.callback_query.message:
            try:  # noqa: SIM105
                await error.update.callback_query.message.delete()
            except TelegramBadRequest:
                pass  # whatever
        # Отправляем уведомление пользователю
        try:
            await error.update.callback_query.answer(
                "⚠️ Сессия истекла. Возвращаю в главное меню...",
                show_alert=False,
            )
        except Exception as e:
            logger.error(f"Failed to send callback answer: {e}")
    elif error.update.message:
        # Для обычных сообщений отправляем ответ
        try:
            await error.update.message.answer(
                "⚠️ Сессия истекла. Используй /start для перезапуска бота."
            )
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
        return

    # Получаем пользователя из middleware_data
    user: Employee | None = dialog_manager.middleware_data.get("user")

    # Определяем роль пользователя и запускаем соответствующее меню
    if user and hasattr(user, "role") and user.role:
        role = user.role

        # Маппинг ролей на состояния главного меню
        role_menu_mapping = {
            "root": RootSG.menu,
            "admin": AdminSG.menu,
            "head": HeadSG.menu,
            "gok": GokSG.menu,
            "mip": MipSG.menu,
            "user": UserSG.menu,
        }

        menu_state = role_menu_mapping.get(role, UserSG.menu)
        logger.info(f"Redirecting user {user.user_id} to {role} menu")
    else:
        # Если роль не определена, отправляем в меню по умолчанию
        menu_state = UserSG.menu
        logger.info("Redirecting to default menu (UserSG.menu)")

    # Запускаем соответствующее меню
    await dialog_manager.start(menu_state, mode=StartMode.RESET_STACK)


def register_middlewares(
    dp: Dispatcher,
    config: Config,
    bot: Bot,
    main_session_pool=None,
    kpi_session_pool=None,
) -> None:
    """Установка middleware для определенных ивентов.

    Args:
        dp: Диспетчер ивентов
        config: Конфигурация
        bot: Экземпляр бота
        main_session_pool: Сессия с базой данных STP
        kpi_session_pool: Сессия с базой данных KPI
    """
    config_middleware = ConfigMiddleware(config)
    database_middleware = DatabaseMiddleware(
        config=config,
        bot=bot,
        stp_session_pool=main_session_pool,
        kpi_session_pool=kpi_session_pool,
    )
    users_middleware = UsersMiddleware()
    groups_middleware = GroupsMiddleware()

    for middleware in [
        config_middleware,
        database_middleware,
        users_middleware,
        groups_middleware,
    ]:
        dp.message.outer_middleware(middleware)
        dp.callback_query.outer_middleware(middleware)
        dp.inline_query.outer_middleware(middleware)
        dp.my_chat_member.outer_middleware(middleware)
        dp.chat_member.outer_middleware(middleware)


def get_storage(config) -> RedisStorage | MemoryStorage:
    """Возвращает хранилище исходя из конфигурации.

    Args:
        config: Объект конфигурации

    Returns:
        Хранилище RedisStorage или MemoryStorage
    """
    if config.tg_bot.use_redis:
        return RedisStorage.from_url(
            config.redis.dsn(),
            key_builder=DefaultKeyBuilder(with_bot_id=True, with_destiny=True),
        )
    else:
        return MemoryStorage()


async def main() -> None:
    """Основная функция запуска бота."""
    setup_logging()

    storage = get_storage(bot_config)

    bot = Bot(
        token=bot_config.tg_bot.token,
        default=DefaultBotProperties(parse_mode="HTML", link_preview_is_disabled=True),
    )

    # Определение команд для приватных чатов
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="whois", description="Поиск сотрудников"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
    )
    await bot.set_my_commands(
        commands=[
            BotCommand(command="balance", description="Баланс баллов"),
            BotCommand(command="top", description="Топ группы по баллам"),
            BotCommand(command="slots", description="Сыграть в слоты"),
            BotCommand(command="dice", description="Сыграть в кубик"),
            BotCommand(command="darts", description="Сыграть в дартс"),
            BotCommand(command="bowling", description="Сыграть в боулинг"),
            BotCommand(
                command="whois", description="Проверить информацию о сотруднике"
            ),
            BotCommand(
                command="admins", description="Проверить список администраторов"
            ),
        ],
        scope=BotCommandScopeAllGroupChats(),
    )
    await bot.set_my_commands(
        commands=[
            BotCommand(
                command="whois", description="Проверить информацию о сотруднике"
            ),
            BotCommand(
                command="pin", description="Закрепить сообщение (ответом на него)"
            ),
            BotCommand(
                command="unpin", description="Открепить сообщение (ответом на него)"
            ),
            BotCommand(command="mute", description="Замутить пользователя"),
            BotCommand(command="unmute", description="Размутить пользователя"),
            BotCommand(command="ban", description="Забанить пользователя"),
            BotCommand(command="unban", description="Разбанить пользователя"),
            BotCommand(command="settings", description="Настройки группы"),
            BotCommand(command="slots", description="Сыграть в слоты"),
            BotCommand(command="dice", description="Сыграть в кубик"),
            BotCommand(command="darts", description="Сыграть в дартс"),
            BotCommand(command="bowling", description="Сыграть в боулинг"),
        ],
        scope=BotCommandScopeAllChatAdministrators(),
    )

    dp = Dispatcher(storage=storage)

    # Создаем движки для доступа к базам
    main_db_engine = create_engine(bot_config.db, db_name=bot_config.db.main_db)
    kpi_db_engine = create_engine(bot_config.db, db_name=bot_config.db.kpi_db)

    main_db = create_session_pool(main_db_engine)
    kpi_db = create_session_pool(kpi_db_engine)

    # Храним сессии в диспетчере для доступа из error handlers
    dp["main_db"] = main_db
    dp["kpi_db"] = kpi_db

    dp.include_routers(*routers_list)
    dp.include_routers(*dialogs_list)
    dp.include_routers(*common_dialogs_list)
    setup_dialogs(dp)

    register_middlewares(dp, bot_config, bot, main_db, kpi_db)

    # Регистрация обработчиков ошибок
    dp.errors.register(_unknown_intent, ExceptionTypeFilter(UnknownIntent))
    dp.errors.register(_unknown_intent, ExceptionTypeFilter(OutdatedIntent))
    dp.errors.register(_unknown_intent, ExceptionTypeFilter(UnknownState))

    # Запуск планировщика и добавление задач
    scheduler_manager = SchedulerManager()
    scheduler_manager.setup_jobs(main_db, bot, kpi_db)
    scheduler_manager.start()

    await on_startup()
    try:
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "callback_query",
                "inline_query",
                "my_chat_member",
                "chat_member",
            ],
        )
    finally:
        await main_db_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Bot was interrupted by the user!")
