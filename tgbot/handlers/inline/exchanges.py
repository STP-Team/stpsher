import logging
from typing import List

from aiogram import Bot
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Message,
)
from aiogram.utils.deep_linking import create_start_link
from aiogram_dialog import DialogManager
from stp_database import Employee, Exchange, MainRequestsRepo

from tgbot.dialogs.getters.common.exchanges.exchanges import (
    get_exchange_text,
)
from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.dialogs.states.user import UserSG
from tgbot.misc.helpers import format_currency_price, tz_perm

logger = logging.getLogger(__name__)


async def handle_exchange_query(
    query_text: str, stp_repo: MainRequestsRepo, user: Employee, bot: Bot
) -> List[InlineQueryResultArticle]:
    """Обработка inline запросов сделок.

    Args:
        query_text: Текст запроса
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee
        bot: Экземпляр бота

    Returns:
        Список найденных сделок
    """
    try:
        # Определяем тип чата из префикса
        use_random_currency_in_content = False
        if query_text.startswith("group_"):
            use_random_currency_in_content = True
            # Убираем префикс group_
            query_text = query_text[6:]
        elif query_text.startswith("dm_"):
            use_random_currency_in_content = False
            # Убираем префикс dm_
            query_text = query_text[3:]
        else:
            # Старый формат без префикса - используем случайную валюту (для обратной совместимости)
            use_random_currency_in_content = True

        exchange_id = query_text.split("_")[1]
        exchange = await stp_repo.exchange.get_exchange_by_id(int(exchange_id))
        if not exchange:
            return []

        # Форматирование информации о сделке для описания (с рублями)
        shift_date, shift_time, description_price_text = await _format_exchange_info(
            exchange, use_random_currency=False
        )

        # Форматирование информации о сделке для сообщения (валюта зависит от типа чата)
        exchange_info = await get_exchange_text(
            stp_repo,
            exchange,
            user.user_id,
            use_random_currency=use_random_currency_in_content,
        )
        message_text = f"🔍 <b>Детали сделки</b>\n\n{exchange_info}"

        deeplink = await create_start_link(
            bot=bot, payload=f"exchange_{exchange.id}", encode=True
        )

        return [
            InlineQueryResultArticle(
                id=f"exchange_{exchange.id}",
                title=f"Сделка #{exchange.id}",
                description=f"📅 Предложение: {shift_time} {shift_date} ПРМ\n💰 Цена: {description_price_text}",
                input_message_content=InputTextMessageContent(
                    message_text=message_text, parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🎭 Открыть сделку",
                                url=deeplink,
                            )
                        ]
                    ]
                ),
            )
        ]
    except (ValueError, IndexError) as e:
        logger.error(f"[Inline] Ошибка получения информации о сделке: {e}")
        return []


async def _format_exchange_info(
    exchange: Exchange, use_random_currency: bool = False
) -> tuple[str, str, str]:
    """Форматирование информации о сделке в удобочитаемый вид.

    Args:
        exchange: Экземпляр сделки с моделью Exchange
        use_random_currency: Использовать случайную валюту вместо рублей

    Returns:
        Форматированная информация о сделке
    """
    # Обрабатываем время
    start_time = exchange.start_time
    if start_time.tzinfo is None:
        start_time = tz_perm.localize(start_time)

    shift_date = start_time.strftime("%d.%m.%Y")
    start_time_str = start_time.strftime("%H:%M")

    if exchange.end_time:
        end_time = exchange.end_time
        if end_time.tzinfo is None:
            end_time = tz_perm.localize(end_time)
        end_time_str = end_time.strftime("%H:%M")
    else:
        end_time_str = "??:??"

    shift_time = f"{start_time_str}-{end_time_str}"
    price_display = format_currency_price(
        exchange.price, exchange.total_price, use_random_currency
    )

    return shift_date, shift_time, price_display


async def handle_user_exchanges(
    query_text: str, stp_repo: MainRequestsRepo, user: Employee, bot: Bot
) -> List[InlineQueryResultArticle]:
    """Обработка inline запросов пользовательских сделок.

    Args:
        query_text: Текст запроса
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee
        bot: Экземпляр бота

    Returns:
        Список активных сделок пользователя
    """
    try:
        # Определяем тип чата из префикса
        use_random_currency_in_content = False
        if query_text.startswith("group_"):
            use_random_currency_in_content = True
        elif query_text.startswith("dm_"):
            use_random_currency_in_content = False
        else:
            # Старый формат без префикса - используем случайную валюту (для обратной совместимости)
            use_random_currency_in_content = True

        # Получаем активные сделки пользователя
        exchanges = await stp_repo.exchange.get_user_exchanges(
            user.user_id, status="active"
        )

        if not exchanges:
            return [
                InlineQueryResultArticle(
                    id="no_exchanges",
                    title="📭 Нет активных сделок",
                    description="У тебя пока нет активных сделок",
                    input_message_content=InputTextMessageContent(
                        message_text="📭 <b>Нет активных сделок</b>\n\nУ тебя пока нет активных сделок.",
                        parse_mode="HTML",
                    ),
                )
            ]

        results = []
        for exchange in exchanges:
            # Форматирование информации о сделке для описания (с рублями)
            (
                shift_date,
                shift_time,
                description_price_text,
            ) = await _format_exchange_info(exchange, use_random_currency=False)

            # Форматирование информации о сделке для сообщения (валюта зависит от типа чата)
            exchange_info = await get_exchange_text(
                stp_repo,
                exchange,
                user.user_id,
                use_random_currency=use_random_currency_in_content,
            )
            message_text = f"🔍 <b>Детали сделки</b>\n\n{exchange_info}"

            deeplink = await create_start_link(
                bot=bot, payload=f"exchange_{exchange.id}", encode=True
            )

            # Определяем статус сделки для иконки
            status_icon = "🟢" if exchange.status == "active" else "🟡"

            results.append(
                InlineQueryResultArticle(
                    id=f"user_exchange_{exchange.id}",
                    title=f"{status_icon} Сделка #{exchange.id}",
                    description=f"📅 {shift_time} {shift_date} ПРМ\n💰 {description_price_text}",
                    input_message_content=InputTextMessageContent(
                        message_text=message_text, parse_mode="HTML"
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="🎭 Открыть сделку",
                                    url=deeplink,
                                )
                            ]
                        ]
                    ),
                )
            )

        return results

    except Exception as e:
        logger.error(f"[Inline] Ошибка получения пользовательских сделок: {e}")
        return [
            InlineQueryResultArticle(
                id="exchanges_error",
                title="❌ Ошибка",
                description="Не удалось загрузить твои сделки",
                input_message_content=InputTextMessageContent(
                    message_text="❌ <b>Ошибка</b>\n\nНе удалось загрузить твои сделки",
                    parse_mode="HTML",
                ),
            )
        ]


async def handle_exchange_cancellation(
    message: Message,
    user: Employee,
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    exchange_id: int,
) -> None:
    """Обрабатывает запрос на отмену сделки.

    Args:
        message: Сообщение пользователя
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога
        exchange_id: ID сделки для отмены
    """
    from datetime import datetime

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from aiogram.utils.deep_linking import create_start_link
    from aiogram_dialog import StartMode

    from tgbot.misc.helpers import format_fullname, tz_perm

    try:
        # Получаем информацию о сделке
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)

        if not exchange:
            await message.answer("❌ Сделка не найдена")
            await dialog_manager.start(UserSG.menu, mode=StartMode.RESET_STACK)
            return

        # Проверяем, что пользователь является участником сделки
        is_participant = (
            exchange.owner_id == user.user_id or exchange.counterpart_id == user.user_id
        )

        if not is_participant:
            await message.answer("❌ Вы не являетесь участником данной сделки")
            await dialog_manager.start(UserSG.menu, mode=StartMode.RESET_STACK)
            return

        # Проверяем статус сделки
        if exchange.status != "sold":
            await message.answer("❌ Отменить можно только завершенные сделки")
            await dialog_manager.start(UserSG.menu, mode=StartMode.RESET_STACK)
            return

        # Проверяем, не наступило ли время начала сделки
        if exchange.start_time and tz_perm.localize(
            exchange.start_time
        ) <= datetime.now(tz=tz_perm):
            await message.answer(
                "❌ Нельзя отменить сделку после наступления времени начала"
            )
            await dialog_manager.start(UserSG.menu, mode=StartMode.RESET_STACK)
            return

        # Отменяем сделку
        await stp_repo.exchange.update_exchange(exchange_id, status="canceled")

        # Определяем другого участника для уведомления
        other_participant_id = (
            exchange.counterpart_id
            if exchange.owner_id == user.user_id
            else exchange.owner_id
        )

        if other_participant_id:
            try:
                # Получаем информацию о пользователе, который отменил сделку
                user_fullname = format_fullname(user, True, True)

                # Создаем deeplink для просмотра отмененной сделки
                exchange_deeplink = await create_start_link(
                    bot=message.bot, payload=f"exchange_{exchange.id}", encode=True
                )

                # Отправляем уведомление другому участнику
                await message.bot.send_message(
                    chat_id=other_participant_id,
                    text=f"""✅ <b>Сделка отменена</b>

🤝 Партнер: {user_fullname}
🏷️ Номер сделки: #{exchange.id}

Сделка №{exchange.id} была отменена по взаимному согласию.""",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="🎭 Открыть сделку",
                                    url=exchange_deeplink,
                                )
                            ]
                        ]
                    ),
                )
            except Exception as e:
                logger.error(
                    f"Ошибка отправки уведомления об отмене сделки {exchange_id}: {e}"
                )

        # Подтверждаем отмену пользователю
        await message.answer("✅ Сделка успешно отменена")

        # Переходим к детальному просмотру отмененной сделки
        await dialog_manager.start(
            Exchanges.my_detail,
            mode=StartMode.RESET_STACK,
            data={"exchange_id": exchange_id},
        )

    except Exception as e:
        logger.error(f"Ошибка при отмене сделки {exchange_id}: {e}")
        await message.answer("❌ Произошла ошибка при отмене сделки")
        await dialog_manager.start(UserSG.menu, mode=StartMode.RESET_STACK)
