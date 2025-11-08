import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from stp_database import Employee, MainRequestsRepo

from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.misc.helpers import tz_perm

logger = logging.getLogger(__name__)

exchange_reschedule_router = Router()
exchange_reschedule_router.callback_query.filter(F.message.chat.type == "private")


def calculate_next_timeslot(current_datetime: datetime) -> datetime:
    """Вычисляет следующий доступный получасовой интервал (:00 или :30).

    Args:
        current_datetime: Текущее время

    Returns:
        datetime: Следующий доступный получасовой интервал
    """
    current_time = current_datetime.time()

    # Вычисляем следующий доступный получасовой интервал (:00 или :30)
    if current_time.minute < 30:
        # Округляем ВВЕРХ к :30 текущего часа
        next_slot_start = current_datetime.replace(minute=30, second=0, microsecond=0)
    else:
        # Округляем ВВЕРХ к :00 следующего часа
        next_slot_start = current_datetime.replace(
            minute=0, second=0, microsecond=0
        ) + timedelta(hours=1)

    return next_slot_start


@exchange_reschedule_router.callback_query(F.data.startswith("reschedule_"))
async def handle_exchange_reschedule(
    callback: CallbackQuery,
    user: Employee,
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик автоматического переноса истекшей сделки.

    Args:
        callback: Callback query от Telegram
        user: Авторизованный пользователь
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалогов
    """
    try:
        # Извлекаем ID сделки из callback_data
        exchange_id = int(callback.data.split("_")[1])

        # Получаем сделку из базы данных
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange:
            await callback.answer("❌ Сделка не найдена", show_alert=True)
            return

        # Проверяем права доступа (пользователь должен быть владельцем сделки)
        if exchange.owner_id != user.user_id:
            await callback.answer("❌ У вас нет прав на эту сделку", show_alert=True)
            return

        # Проверяем тип сделки
        if exchange.owner_intent != "sell":
            await callback.answer(
                "❌ Автоматический перенос доступен только для продаж", show_alert=True
            )
            return

        # Проверяем статус сделки
        if exchange.status != "expired":
            await callback.answer("❌ Сделка должна быть просроченной", show_alert=True)
            return

        # Получаем текущее время в локальной зоне
        current_local_time = datetime.now(tz_perm)

        # Проверяем наличие времени окончания
        if not exchange.end_time:
            await callback.answer(
                "❌ Не удалось определить время окончания сделки", show_alert=True
            )
            return

        # Убеждаемся, что end_time timezone-aware для проверок
        original_end = exchange.end_time
        if original_end.tzinfo is None:
            original_end = tz_perm.localize(original_end)

        # Проверяем, что сделка сегодня
        today = current_local_time.date()
        if original_end.date() != today:
            await callback.answer(
                "❌ Можно переносить только сделки текущего дня", show_alert=True
            )
            return

        # Проверяем, что время окончания еще не прошло
        if original_end <= current_local_time:
            await callback.answer(
                "❌ Время окончания сделки уже прошло, перенос невозможен",
                show_alert=True,
            )
            return

        # Вычисляем следующий доступный временной слот
        new_start_time = calculate_next_timeslot(current_local_time)

        # Проверяем, что между новым началом и концом минимум 30 минут
        time_remaining = original_end - new_start_time
        if time_remaining < timedelta(minutes=30):
            await callback.answer(
                "❌ До окончания сделки осталось меньше 30 минут, перенос невозможен",
                show_alert=True,
            )
            return

        # Обновляем только время начала сделки (end_time остается прежним)
        success = await stp_repo.exchange.update_exchange_date(
            exchange_id=exchange_id,
            start_time=new_start_time.replace(
                tzinfo=None
            ),  # Сохраняем как naive datetime
            end_time=exchange.end_time,  # Оставляем оригинальное время окончания
        )

        if not success:
            await callback.answer(
                "❌ Ошибка при обновлении времени сделки", show_alert=True
            )
            return

        # Обновляем статус сделки на активный
        await stp_repo.exchange.update_exchange(exchange_id, status="active")
        await stp_repo.session.commit()

        # Отправляем подтверждение
        new_start_str = new_start_time.strftime("%H:%M")
        original_end_str = original_end.strftime("%H:%M")
        await callback.answer(
            f"✅ Начало сделки перенесено на {new_start_str} (до {original_end_str})",
            show_alert=True,
        )

        # Запускаем диалог детального просмотра сделки
        await dialog_manager.start(
            Exchanges.my_detail,
            mode=StartMode.RESET_STACK,
            data={"exchange_id": exchange_id},
        )

        logger.info(
            f"Пользователь {user.user_id} автоматически перенес начало сделки {exchange_id} на {new_start_str} (до {original_end_str})"
        )

    except ValueError:
        await callback.answer("❌ Неверный формат данных", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при автоматическом переносе сделки: {e}")
        await callback.answer(
            "❌ Произошла ошибка при переносе сделки", show_alert=True
        )
