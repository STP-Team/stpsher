import logging
from typing import List

from aiogram import Bot, Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from stp_database.models.STP import Employee
from stp_database.repo.STP import MainRequestsRepo

from tgbot.filters.role import (
    AdminFilter,
    DutyFilter,
    MipFilter,
    MultiRoleFilter,
    SpecialistFilter,
)
from tgbot.handlers.inline.exchanges import handle_exchange_query, handle_user_exchanges
from tgbot.handlers.inline.helpers import CACHE_TIMES
from tgbot.handlers.inline.search import InlineResultBuilder, handle_search_query
from tgbot.handlers.inline.subscriptions import handle_subscription_query
from tgbot.services.files_processing.formatters.schedule import get_current_month
from tgbot.services.files_processing.handlers.schedule import schedule_service

logger = logging.getLogger(__name__)

user_inline_router = Router()
user_inline_router.inline_query.filter(
    MultiRoleFilter(
        SpecialistFilter(),
        AdminFilter(),
        MipFilter(),
        MipFilter(),
        DutyFilter(),
    )
)


@user_inline_router.inline_query()
async def inline_handler(
    inline_query: InlineQuery, user: Employee, stp_repo: MainRequestsRepo, bot: Bot
) -> None:
    """Обработчик для inline запросов.

    Args:
        inline_query: Inline запрос пользователя
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        bot: Экземпляр бота
    """
    query_text = inline_query.query.strip()

    try:
        # Обрабатываем неавторизованных пользователей
        if not user:
            results = [
                InlineQueryResultArticle(
                    id="auth_help",
                    title="❌ Требуется авторизация",
                    description="Авторизуйся в боте для использования функций",
                    input_message_content=InputTextMessageContent(
                        message_text="/start"
                    ),
                )
            ]
        else:
            # Роутинг специфичных запросов
            if (
                query_text.startswith("group_exchange_")
                or query_text.startswith("dm_exchange_")
                or "exchange_" in query_text
            ):
                results = await handle_exchange_query(query_text, stp_repo, user, bot)
            elif (
                query_text.startswith("group_my_exchanges")
                or query_text.startswith("dm_my_exchanges")
                or "my_exchanges" in query_text
            ):
                results = await handle_user_exchanges(query_text, stp_repo, user, bot)
            elif "subscription_" in query_text:
                results = await handle_subscription_query(query_text, stp_repo, bot)
            else:
                if query_text and len(query_text) >= 2:
                    results = await handle_search_query(query_text, stp_repo)
                else:
                    results = await create_default_commands(user, stp_repo)

        # Устанавливаем кеш ответу
        cache_time = get_cache_time(query_text, results)
        await inline_query.answer(results, cache_time=cache_time, is_personal=True)

    except Exception as e:
        logger.error(
            f"[Inline] Ошибка при обработке запроса '{query_text}': {e}",
            exc_info=True,
        )
        # Возвращаем ошибку
        error_result = InlineResultBuilder.create_error_result(e)
        await inline_query.answer(
            [error_result], cache_time=CACHE_TIMES["NO_CACHE"], is_personal=True
        )


async def create_default_commands(
    user: Employee, stp_repo: MainRequestsRepo
) -> List[InlineQueryResultArticle]:
    """Создание дефолтных команд."""
    results = []

    # Мой график
    try:
        current_month = get_current_month()
        schedule_text = await schedule_service.get_user_schedule_response(
            user=user, month=current_month, compact=True
        )
        if schedule_text:
            results.append(
                InlineQueryResultArticle(
                    id="schedule_option",
                    title="📅 Мой график",
                    description=f"Твой график на {current_month}",
                    input_message_content=InputTextMessageContent(
                        message_text=schedule_text
                    ),
                )
            )
    except Exception as e:
        logger.error(
            f"[Inline] Ошибка получения графика для {user.id}: {e}", exc_info=True
        )

    # Дежурные на сегодня
    try:
        duties_text = await schedule_service.get_duties_response(
            division=user.division, stp_repo=stp_repo
        )
        if duties_text:
            results.append(
                InlineQueryResultArticle(
                    id="duties_option",
                    title="👮‍♂️ Дежурные на сегодня",
                    description=f"График дежурных {user.division}",
                    input_message_content=InputTextMessageContent(
                        message_text=duties_text
                    ),
                )
            )
    except Exception as e:
        logger.error(
            f"[Inline] Ошибка получения графика дежурных для {user.division}: {e}",
            exc_info=True,
        )

    # Руководители на сегодня
    try:
        heads_text = await schedule_service.get_heads_response(
            division=user.division, stp_repo=stp_repo
        )
        if heads_text:
            results.append(
                InlineQueryResultArticle(
                    id="heads_option",
                    title="👑 Руководители на сегодня",
                    description=f"График руководителей {user.division}",
                    input_message_content=InputTextMessageContent(
                        message_text=heads_text
                    ),
                )
            )
    except Exception as e:
        logger.error(
            f"[Inline] Ошибка получения графика руководителей для {user.division}: {e}",
            exc_info=True,
        )

    return results


def get_cache_time(query_text: str, results: List[InlineQueryResultArticle]) -> int:
    """Определение времени кеширования в зависимости от запроса.

    Args:
        query_text: Текст запроса
        results: Результаты

    Returns:
        Время кеширования в секундах
    """
    if not query_text:
        # Стандартные команды
        return CACHE_TIMES["DEFAULT_COMMANDS"]
    elif len(results) == 0 or any(result.id.endswith("_error") for result in results):
        # Не кешируем ошибки или пустые результаты
        return CACHE_TIMES["NO_CACHE"]
    elif "exchange_" in query_text:
        # Кешируем детали сделки
        return CACHE_TIMES["EXCHANGE_DETAILS"]
    elif "my_exchanges" in query_text:
        # Кешируем список активных сделок
        return CACHE_TIMES["MY_EXCHANGES"]
    elif "subscription_" in query_text:
        # Кешируем детали подписки
        return CACHE_TIMES["SUBSCRIPTION_DETAILS"]
    else:
        # Кешируем результаты поиска
        return CACHE_TIMES["SEARCH_RESULTS"]
