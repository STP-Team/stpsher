"""Фильтры для проверки доступа к казино в группах."""

from aiogram.dispatcher.event.bases import CancelHandler
from aiogram.filters import BaseFilter
from aiogram.types import Message
from stp_database import Employee, MainRequestsRepo

from tgbot.misc.helpers import format_fullname


class IsGroupCasinoAllowed(BaseFilter):
    """Фильтр проверки доступа к казино в группе.

    Проверяет:
    1. Зарегистрирована ли группа в базе данных
    2. Разрешен ли казино в группе (is_casino_allowed=True)
    3. Разрешен ли доступ к казино пользователю (is_casino_allowed=True)

    При отсутствии любого из условий отправляет пользователю соответствующее сообщение об ошибке.
    """

    async def __call__(
        self, message: Message, user: Employee, stp_repo: MainRequestsRepo, **kwargs
    ) -> bool:
        """Проверяет разрешен ли доступ к казино для пользователя и группы.

        Args:
            message: Входящее сообщение
            user: Экземпляр пользователя с моделью Employee
            stp_repo: Репозиторий операций с базой STP
            **kwargs: Дополнительные аргументы.

        Returns:
            True если доступ разрешен.

        Raises:
            CancelHandler: Если доступ запрещен (после отправки сообщения об ошибке).
        """
        if user and not user.is_casino_allowed:
            user_head = await stp_repo.employee.get_users(fullname=user.head)
            head_fullname = format_fullname(user_head, True, True)
            await message.reply(
                "✋ <b>Доступ к казино запрещен</b>\n\n"
                f"Обратись к <b>{head_fullname}</b> для получения доступа"
            )
            raise CancelHandler()

        # Проверяем группу
        try:
            group = await stp_repo.group.get_groups(message.chat.id)
            if not group:
                await message.reply(
                    "✋ <b>Группа не зарегистрирована</b>\n\n"
                    "Обратись к администратору/владельцу группы для ее регистрации. После регистрации группы появится возможность использовать казино"
                )
                raise CancelHandler()

            if not group.is_casino_allowed:
                await message.reply("✋ <b>Казино отключено в группе</b>")
                raise CancelHandler()
        except Exception:
            # Если ошибка при получении группы - запрещаем доступ
            await message.reply("🚨 <b>Ошибка доступа к базе данных</b>")
            raise CancelHandler()

        return True
