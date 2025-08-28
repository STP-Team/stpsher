import logging

from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from infrastructure.database.models import User
from tgbot.handlers.user.schedule.main import schedule_service

logger = logging.getLogger(__name__)

user_inline_router = Router()


@user_inline_router.inline_query()
async def inline_help(inline_query: InlineQuery, user: User, stp_repo):
    """Обработчик общих инлайн-запросов с подсказками"""
    if not user:
        results = [
            InlineQueryResultArticle(
                id="auth_help",
                title="❌ Требуется авторизация",
                description="Авторизуйтесь в боте для использования функций",
                input_message_content=InputTextMessageContent(
                    message_text="❌ Для использования функций бота необходимо авторизоваться @stpsher_bot"
                ),
            )
        ]
    else:
        results = []

        # Мой график - получаем реальные данные
        try:
            current_month = schedule_service.get_current_month()
            schedule_text = await schedule_service.get_user_schedule_response(
                user=user, month=current_month, compact=True
            )
            results.append(
                InlineQueryResultArticle(
                    id="schedule_option",
                    title="📅 Мой график",
                    description=f"График {user.fullname} на {current_month}",
                    input_message_content=InputTextMessageContent(
                        message_text=schedule_text, parse_mode="HTML"
                    ),
                )
            )
        except Exception as e:
            logger.error(f"Error getting schedule for inline help: {e}")
            results.append(
                InlineQueryResultArticle(
                    id="schedule_error",
                    title="📅 Мой график",
                    description="Ошибка при получении графика",
                    input_message_content=InputTextMessageContent(
                        message_text=f"❌ Ошибка при получении графика: {e}"
                    ),
                )
            )

        # Дежурные на сегодня - получаем реальные данные
        try:
            duties_text = await schedule_service.get_duties_response(
                division=user.division, stp_repo=stp_repo
            )
            results.append(
                InlineQueryResultArticle(
                    id="duties_option",
                    title="👮‍♂️ Дежурные на сегодня",
                    description=f"Дежурные по направлению {user.division}",
                    input_message_content=InputTextMessageContent(
                        message_text=duties_text, parse_mode="HTML"
                    ),
                )
            )
        except Exception as e:
            logger.error(f"Error getting duties for inline help: {e}")
            results.append(
                InlineQueryResultArticle(
                    id="duties_error",
                    title="👮‍♂️ Дежурные на сегодня",
                    description="Ошибка при получении дежурных",
                    input_message_content=InputTextMessageContent(
                        message_text=f"❌ Ошибка при получении дежурных: {e}"
                    ),
                )
            )

        # Руководители на сегодня - получаем реальные данные
        try:
            heads_text = await schedule_service.get_heads_response(
                division=user.division, stp_repo=stp_repo
            )
            results.append(
                InlineQueryResultArticle(
                    id="heads_option",
                    title="👔 Руководители на сегодня",
                    description=f"Руководители по направлению {user.division}",
                    input_message_content=InputTextMessageContent(
                        message_text=heads_text, parse_mode="HTML"
                    ),
                )
            )
        except Exception as e:
            logger.error(f"Error getting heads for inline help: {e}")
            results.append(
                InlineQueryResultArticle(
                    id="heads_error",
                    title="👔 Руководители на сегодня",
                    description="Ошибка при получении руководителей",
                    input_message_content=InputTextMessageContent(
                        message_text=f"❌ Ошибка при получении руководителей: {e}"
                    ),
                )
            )

    await inline_query.answer(results, cache_time=60, is_personal=True)
