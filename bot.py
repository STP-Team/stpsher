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
    BotCommandScopeAllPrivateChats,
    ErrorEvent,
)
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram_dialog import DialogManager, StartMode, setup_dialogs
from aiogram_dialog.api.exceptions import OutdatedIntent, UnknownIntent, UnknownState
from aiohttp import web
from aiohttp.web import Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from stp_database import create_engine, create_session_pool
from stp_database.repo.STP import MainRequestsRepo

from tgbot.config import Config, load_config
from tgbot.dialogs.menus import common_dialogs_list, dialogs_list
from tgbot.dialogs.states.admin import AdminSG
from tgbot.dialogs.states.gok import GokSG
from tgbot.dialogs.states.head import HeadSG
from tgbot.dialogs.states.mip import MipSG
from tgbot.dialogs.states.root import RootSG
from tgbot.dialogs.states.user import UserSG
from tgbot.handlers import routers_list
from tgbot.middlewares.AccessMiddleware import AccessMiddleware
from tgbot.middlewares.ConfigMiddleware import ConfigMiddleware
from tgbot.middlewares.DatabaseMiddleware import DatabaseMiddleware
from tgbot.middlewares.EventLoggingMiddleware import EventLoggingMiddleware
from tgbot.middlewares.GroupsMiddleware import GroupsMiddleware
from tgbot.middlewares.UsersMiddleware import UsersMiddleware
from tgbot.misc.dicts import roles
from tgbot.misc.helpers import short_name
from tgbot.services.files_processing.core.cache import warm_cache_on_startup
from tgbot.services.logger import setup_logging
from tgbot.services.schedulers.scheduler import SchedulerManager

bot_config = load_config(".env")

logger = logging.getLogger(__name__)


async def on_startup():
    """Функция, активируемая при запуске основного процесса бота."""
    logger.info("[Startup] Начинаем прогрев кэша Excel файлов...")

    try:
        # Запускаем прогрев кэша в отдельной задаче
        def run_cache_warming():
            try:
                stats = warm_cache_on_startup("uploads")
                logger.info(
                    f"[Startup] Прогрев кэша завершен: {stats['processed_files']} файлов обработано, "
                    f"{stats['successful_sheets']} листов загружено успешно"
                )
                if stats["errors"]:
                    logger.warning(
                        f"[Startup] Ошибки при прогреве кэша: {len(stats['errors'])} шт."
                    )
            except Exception as e:
                logger.error(f"[Startup] Ошибка при прогреве кэша: {e}")

        # Запускаем в отдельном потоке, чтобы не блокировать запуск бота
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, run_cache_warming)

        logger.info("[Startup] Прогрев кэша запущен в фоновом режиме")

    except Exception as e:
        logger.error(f"[Startup] Не удалось запустить прогрев кэша: {e}")


async def _unknown_intent(error: ErrorEvent, dialog_manager: DialogManager):
    """Обработчик ошибки UnknownIntent - возвращает пользователя в главное меню.

    Args:
        error: Событие ошибки с информацией об исключении и обновлении
        dialog_manager: Менеджер диалога
    """
    logger.warning("[Редирект] Рестарт диалога: %s", error.exception)

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

    # Получаем пулы сессий из middleware_data
    stp_session_pool = dialog_manager.middleware_data["stp_session_pool"]
    stats_session_pool = dialog_manager.middleware_data["stats_session_pool"]

    if not stp_session_pool or not stats_session_pool:
        logger.error("Session pools not available in middleware_data")
        return

    # Создаем репозитории для работы с базами данных
    try:
        async with stp_session_pool() as stp_session:
            stp_repo = MainRequestsRepo(stp_session)

            # Получаем пользователя из базы данных
            if error.update.callback_query:
                user_id = error.update.callback_query.from_user.id
            elif error.update.message:
                user_id = error.update.message.from_user.id
            else:
                logger.error("Unable to determine user_id from update")
                return

            user = await stp_repo.employee.get_users(user_id=user_id)

            async with stats_session_pool() as stats_session:
                from stp_database.repo.Stats.requests import StatsRequestsRepo

                stats_repo = StatsRequestsRepo(stats_session)

                # Добавляем репозитории в middleware_data для геттеров диалогов
                dialog_manager.middleware_data["user"] = user
                dialog_manager.middleware_data["stp_repo"] = stp_repo
                dialog_manager.middleware_data["stats_repo"] = stats_repo
                dialog_manager.middleware_data["stp_session"] = stp_session
                dialog_manager.middleware_data["stats_session"] = stats_session

                # Определяем роль пользователя и запускаем соответствующее меню
                if user and hasattr(user, "role") and user.role:
                    role = str(user.role)

                    # Маппинг ролей на состояния главного меню
                    role_menu_mapping = {
                        "1": UserSG.menu,
                        "2": HeadSG.menu,
                        "3": UserSG.menu,
                        "4": AdminSG.menu,
                        "5": GokSG.menu,
                        "6": MipSG.menu,
                        "10": RootSG.menu,
                    }

                    menu_state = role_menu_mapping.get(role, UserSG.menu)
                    role_name = roles.get(user.role, {}).get("name", "Unknown")
                    logger.info(
                        f"[Редирект] Пользователь {short_name(user.fullname)} ({user.user_id}) перенаправлен в меню роли '{role_name}' (ID: {role})"
                    )
                else:
                    # Если роль не определена, отправляем в меню по умолчанию
                    menu_state = UserSG.menu
                    logger.info(
                        f"[Редирект] Пользователь {short_name(user.fullname)} ({user.user_id}) перенаправлен в стандартное меню (UserSG.menu)"
                    )

                # Запускаем соответствующее меню
                await dialog_manager.start(menu_state, mode=StartMode.RESET_STACK)

    except Exception as e:
        logger.error(f"Failed to restart dialog: {e}")
        return


def register_middlewares(
    dp: Dispatcher,
    config: Config,
    bot: Bot,
    stp_session_pool: async_sessionmaker[AsyncSession],
    stats_session_pool: async_sessionmaker[AsyncSession],
) -> None:
    """Установка middleware для определенных ивентов.

    Args:
        dp: Диспетчер ивентов
        config: Конфигурация
        bot: Экземпляр бота
        stp_session_pool: Пул сессий с базой STP
        stats_session_pool: Пул сессий с базой KPI
    """
    config_middleware = ConfigMiddleware(config)
    database_middleware = DatabaseMiddleware(
        config=config,
        bot=bot,
        stp_session_pool=stp_session_pool,
        stats_session_pool=stats_session_pool,
    )
    users_middleware = UsersMiddleware()
    groups_middleware = GroupsMiddleware()
    event_logging_middleware = EventLoggingMiddleware()
    access_middleware = AccessMiddleware()

    for middleware in [
        config_middleware,
        database_middleware,
        users_middleware,
        groups_middleware,
        event_logging_middleware,
        access_middleware,
    ]:
        dp.message.outer_middleware(middleware)  # noqa
        dp.callback_query.outer_middleware(middleware)
        dp.inline_query.outer_middleware(middleware)
        dp.my_chat_member.outer_middleware(middleware)
        dp.chat_member.outer_middleware(middleware)
        dp.chat_join_request.outer_middleware(middleware)


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


async def on_startup_webhook(bot: Bot, config: Config) -> None:
    """Настройка webhook при запуске бота.

    Args:
        bot: Экземпляр бота
        config: Конфигурация приложения
    """
    webhook_url = f"https://{config.tg_bot.webhook_domain}{config.tg_bot.webhook_path}"
    logger.info(f"[Вебхук] Устанавливаем вебхук: {webhook_url}")

    await bot.set_webhook(
        url=webhook_url,
        allowed_updates=[
            "message",
            "callback_query",
            "inline_query",
            "my_chat_member",
            "chat_member",
            "chat_join_request",
        ],
        drop_pending_updates=True,
        secret_token=config.tg_bot.webhook_secret,
    )
    logger.info("[Вебхук] Вебхук установлен")


async def on_shutdown_webhook(bot: Bot) -> None:
    """Удаление webhook при остановке бота.

    Args:
        bot: Экземпляр бота
    """
    logger.info("[Вебхук] Удаляем вебхук...")
    await bot.delete_webhook()
    logger.info("[Вебхук] Вебхук удален")


async def health_check(_request) -> Response:
    """Эндпоинт для проверки здоровья приложения.

    Args:
        _request: HTTP запрос

    Returns:
        Response: HTTP ответ со статусом здоровья
    """
    return Response(text="OK", status=200)


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
            BotCommand(command="start", description="🏠 Главное меню"),
            BotCommand(command="shop", description="💎 Магазин предметов"),
            BotCommand(command="schedule", description="👔 Мой график"),
            BotCommand(command="exchanges", description="🎭 Биржа подмен"),
            BotCommand(command="kpi", description="🌟 Показатели"),
            BotCommand(command="salary", description="💰 Зарплата"),
            BotCommand(command="whois", description="🕵🏻 Поиск сотрудников"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
    )

    await bot.set_my_commands(
        commands=[
            BotCommand(command="pin", description="📌 Закрепить сообщение"),
            BotCommand(command="mute", description="🤐 Заглушить пользователя"),
            BotCommand(command="ban", description="🚫 Заблокировать пользователя"),
            BotCommand(command="settings", description="⚙️ Настройки группы"),
        ],
        scope=BotCommandScopeAllChatAdministrators(),
    )

    dp = Dispatcher(storage=storage)

    # Создаем движки для доступа к базам
    stp_engine = create_engine(
        db_name=bot_config.db.stp_db,
        host=bot_config.db.host,
        username=bot_config.db.user,
        password=bot_config.db.password,
    )
    stats_engine = create_engine(
        db_name=bot_config.db.stats_db,
        host=bot_config.db.host,
        username=bot_config.db.user,
        password=bot_config.db.password,
    )

    stp_session_pool = create_session_pool(stp_engine)
    stats_session_pool = create_session_pool(stats_engine)

    # Храним сессии в диспетчере для доступа из error handlers
    dp["stp_session_pool"] = stp_session_pool
    dp["stats_session_pool"] = stats_session_pool

    dp.include_routers(*routers_list)
    dp.include_routers(*dialogs_list)
    dp.include_routers(*common_dialogs_list)
    setup_dialogs(dp)

    register_middlewares(dp, bot_config, bot, stp_session_pool, stats_session_pool)

    # Регистрация обработчиков ошибок
    dp.errors.register(_unknown_intent, ExceptionTypeFilter(UnknownIntent))
    dp.errors.register(_unknown_intent, ExceptionTypeFilter(OutdatedIntent))
    dp.errors.register(_unknown_intent, ExceptionTypeFilter(UnknownState))

    # Запуск планировщика и добавление задач
    scheduler_manager = SchedulerManager()
    scheduler_manager.setup_jobs(
        stp_session_pool=stp_session_pool,
        stats_session_pool=stats_session_pool,
        bot=bot,
    )
    scheduler_manager.start()

    # await on_startup()

    try:
        if bot_config.tg_bot.use_webhook:
            # Webhook mode
            logger.info("[Режим запуска] Бот запущен в режиме webhooks")
            await on_startup_webhook(bot, bot_config)

            # Создаем aiohttp приложение
            app = web.Application()

            # Регистрируем health check эндпоинт
            app.router.add_get("/health", health_check)

            # Создаем обработчик webhook
            webhook_handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
                secret_token=bot_config.tg_bot.webhook_secret,
            )
            webhook_handler.register(app, path="/")
            setup_application(app, dp, bot=bot)

            # Запускаем веб-сервер
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(
                runner, host="0.0.0.0", port=bot_config.tg_bot.webhook_port
            )
            await site.start()

            logger.info(
                f"[Вебхук] Сервер запущен на порту {bot_config.tg_bot.webhook_port}"
            )

            # Держим сервер запущенным
            await asyncio.Event().wait()

        else:
            # Polling mode
            logger.info("[Режим запуска] Бот запущен в режиме polling")
            await dp.start_polling(
                bot,
                allowed_updates=[
                    "message",
                    "callback_query",
                    "inline_query",
                    "my_chat_member",
                    "chat_member",
                    "chat_join_request",
                ],
            )
    finally:
        if bot_config.tg_bot.use_webhook:
            await on_shutdown_webhook(bot)
        await stp_engine.dispose()
        await stats_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Bot was interrupted by the user!")
