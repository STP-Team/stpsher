import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import NoContextError
from stp_database.models.STP import Employee
from stp_database.repo.STP import MainRequestsRepo

from tgbot.dialogs.states.common.exchanges import Exchanges, ExchangesSub
from tgbot.dialogs.states.common.game import Game
from tgbot.dialogs.states.user import UserSG
from tgbot.handlers.inline.exchanges import handle_exchange_cancellation
from tgbot.keyboards.auth import auth_kb
from tgbot.services.event_logger import EventLogger

logger = logging.getLogger(__name__)


deeplink_router = Router()


@deeplink_router.message(CommandStart(deep_link=True))
async def start_deeplink(
    message: Message,
    user: Employee,
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    event_logger: EventLogger,
) -> None:
    """Обработка deep link запросов при старте бота.

    Args:
        message: Сообщение пользователя
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога
        event_logger: Логер событий
    """
    if not user:
        await message.answer(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    await event_logger.log_bot_start(user.user_id)

    try:
        await dialog_manager.done()
    except NoContextError:
        pass

    # Извлекаем payload из команды /start
    command_args = message.text.split(maxsplit=1)
    if len(command_args) > 1:
        from aiogram.utils.deep_linking import decode_payload

        from tgbot.dialogs.states.common.groups import Groups

        payload = decode_payload(command_args[1])

        # Проверяем, что это запрос на настройки группы
        if payload.startswith("group_"):
            group_id = int(payload.split("_", 1)[1])
            # Запускаем диалог настроек группы
            await dialog_manager.start(
                Groups.group_details,
                mode=StartMode.RESET_STACK,
                data={"group_id": group_id},
            )
            return
        elif payload.startswith("exchange_"):
            exchange_id = int(payload.split("_", 1)[1])
            exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)

            if not exchange:
                await dialog_manager.start(UserSG.menu, mode=StartMode.RESET_STACK)
            else:
                if (
                    exchange.owner_id == user.user_id
                    or exchange.counterpart_id == user.user_id
                ):
                    # Запускаем диалог своей подмены
                    await dialog_manager.start(
                        Exchanges.my_detail,
                        mode=StartMode.RESET_STACK,
                        data={"exchange_id": exchange_id},
                    )
                    return
                if exchange.status != "active":
                    await dialog_manager.start(UserSG.menu, mode=StartMode.RESET_STACK)
                    return
                if exchange.owner_intent == "sell":
                    # Запускаем диалог продаж
                    await dialog_manager.start(
                        Exchanges.buy_detail,
                        mode=StartMode.RESET_STACK,
                        data={"exchange_id": exchange_id},
                    )
                else:
                    # Запускаем диалог покупок
                    await dialog_manager.start(
                        Exchanges.sell_detail,
                        mode=StartMode.RESET_STACK,
                        data={"exchange_id": exchange_id},
                    )
            return
        elif payload.startswith("cancel_"):
            exchange_id = int(payload.split("_", 1)[1])

            # Обрабатываем запрос на отмену сделки
            await handle_exchange_cancellation(
                message, user, stp_repo, dialog_manager, exchange_id
            )
            return
        elif payload.startswith("subscription_"):
            subscription_id = int(payload.split("_", 1)[1])
            subscription = await stp_repo.exchange.get_subscription_by_id(
                subscription_id
            )

            if not subscription:
                await dialog_manager.start(UserSG.menu, mode=StartMode.RESET_STACK)
                return

            # Запускаем диалог подписки
            await dialog_manager.start(
                ExchangesSub.sub_detail,
                mode=StartMode.RESET_STACK,
                data={"subscription_id": subscription_id},
            )
            return
        elif payload.startswith("activation_"):
            purchase_id = int(payload.split("_", 1)[1])
            purchase = await stp_repo.purchase.get_purchase_details(purchase_id)

            if not purchase or purchase.user_purchase.status != "review":
                await dialog_manager.start(UserSG.menu, mode=StartMode.RESET_STACK)
                return

            # Запускаем диалог активации
            await dialog_manager.start(
                Game.activation_details,
                mode=StartMode.RESET_STACK,
                data={"purchase_id": purchase_id},
            )
            return

    # Если payload не распознан, запускаем обычное меню
    await dialog_manager.start(UserSG.menu, mode=StartMode.RESET_STACK)
