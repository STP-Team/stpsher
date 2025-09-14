import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)

from infrastructure.database.setup import create_engine, create_session_pool
from tgbot.config import Config, load_config
from tgbot.handlers import routers_list
from tgbot.middlewares.ConfigMiddleware import ConfigMiddleware
from tgbot.middlewares.DatabaseMiddleware import DatabaseMiddleware
from tgbot.middlewares.UsersMiddleware import UsersMiddleware
from tgbot.services.logger import setup_logging
from tgbot.services.scheduler import SchedulerManager

bot_config = load_config(".env")

logger = logging.getLogger(__name__)


# async def on_startup(bot: Bot):
#     if bot_config.tg_bot.activity_status:
#         timeout_msg = f"Да ({bot_config.tg_bot.activity_warn_minutes}/{bot_config.tg_bot.activity_close_minutes} минут)"
#     else:
#         timeout_msg = "Нет"
#
#     if bot_config.tg_bot.remove_old_questions:
#         remove_topics_msg = (
#             f"Да (старше {bot_config.tg_bot.remove_old_questions_days} дней)"
#         )
#     else:
#         remove_topics_msg = "Нет"
#
#     await bot.send_message(
#         chat_id=bot_config.tg_bot.ntp_forum_id,
#         text=f"""<b>🚀 Запуск</b>
#
# Вопросник запущен со следующими параметрами:
# <b>- Направление:</b> {bot_config.tg_bot.division}
# <b>- Запрашивать регламент:</b> {"Да" if bot_config.tg_bot.ask_clever_link else "Нет"}
# <b>- Закрывать по таймауту:</b> {timeout_msg}
# <b>- Удалять старые вопросы:</b> {remove_topics_msg}
#
# <blockquote>База данных: {"Основная" if bot_config.db.main_db == "STPMain" else "Запасная"}</blockquote>""",
#     )


def register_middlewares(
    dp: Dispatcher,
    config: Config,
    bot: Bot,
    main_session_pool=None,
    kpi_session_pool=None,
):
    """
    Alternative setup with more selective middleware application.
    Use this if you want different middleware chains for different event types.
    """

    config_middleware = ConfigMiddleware(config)
    database_middleware = DatabaseMiddleware(
        config=config,
        bot=bot,
        stp_session_pool=main_session_pool,
        kpi_session_pool=kpi_session_pool,
    )
    users_middleware = UsersMiddleware()

    for middleware in [config_middleware, database_middleware, users_middleware]:
        dp.message.outer_middleware(middleware)
        dp.callback_query.outer_middleware(middleware)
        dp.inline_query.outer_middleware(middleware)
        dp.my_chat_member.outer_middleware(middleware)


def get_storage(config):
    """
    Return storage based on the provided configuration.

    Args:
        config (Config): The configuration object.

    Returns:
        Storage: The storage object based on the configuration.

    """
    if config.tg_bot.use_redis:
        return RedisStorage.from_url(
            config.redis.dsn(),
            key_builder=DefaultKeyBuilder(with_bot_id=True, with_destiny=True),
        )
    else:
        return MemoryStorage()


async def main():
    setup_logging()

    storage = get_storage(bot_config)

    bot = Bot(
        token=bot_config.tg_bot.token,
        default=DefaultBotProperties(parse_mode="HTML", link_preview_is_disabled=True),
    )

    # Определение команд для приватных чатов
    await bot.set_my_commands(
        commands=[BotCommand(command="start", description="Главное меню")],
        scope=BotCommandScopeAllPrivateChats(),
    )
    await bot.set_my_commands(
        commands=[
            BotCommand(
                command="whois", description="Проверить информацию о сотруднике"
            ),
            BotCommand(command="slots", description="Сыграть в слоты"),
            BotCommand(command="dice", description="Сыграть в кубик"),
            BotCommand(command="darts", description="Сыграть в дартс"),
            BotCommand(command="bowling", description="Сыграть в боулинг"),
        ],
        scope=BotCommandScopeAllGroupChats(),
    )

    dp = Dispatcher(storage=storage)

    # Create engines for different databases
    main_db_engine = create_engine(bot_config.db, db_name=bot_config.db.main_db)
    kpi_db_engine = create_engine(bot_config.db, db_name=bot_config.db.kpi_db)

    main_db = create_session_pool(main_db_engine)
    kpi_db = create_session_pool(kpi_db_engine)

    # Store session pools in dispatcher
    dp["main_db"] = main_db
    dp["kpi_db"] = kpi_db

    dp.include_routers(*routers_list)

    register_middlewares(dp, bot_config, bot, main_db, kpi_db)

    # Setup all scheduled jobs using the new scheduler manager
    scheduler_manager = SchedulerManager()
    scheduler_manager.setup_jobs(main_db, bot, kpi_db)
    scheduler_manager.start()

    # await on_startup(bot)
    try:
        await dp.start_polling(bot)
    finally:
        await main_db_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Bot was interrupted by the user!")
