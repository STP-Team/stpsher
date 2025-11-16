"""Фильтры для проверки доступа к казино в группах."""

from aiogram.dispatcher.event.bases import CancelHandler
from aiogram.filters import BaseFilter
from aiogram.types import Message
from stp_database import Employee, MainRequestsRepo


class IsGroupCasinoAllowed(BaseFilter):
    """Фильтр проверки доступа к казино в группе.

    Проверяет:
    1. Зарегистрирована ли группа в базе данных
    2. Разрешен ли казино в группе (is_casino_allowed=True)
    3. Разрешен ли доступ к казино пользователю (is_casino_allowed=True)

    При отсутствии любого из условий прерывает обработку без сообщения.
    """

    async def __call__(
        self, message: Message, user: Employee, stp_repo: MainRequestsRepo, **kwargs
    ) -> bool:
        """Проверяет разрешен ли доступ к казино для пользователя и группы.

        Args:
            message: Входящее сообщение.
            user: Экземпляр пользователя с моделью Employee
            stp_repo: Репозиторий операций с базой STP
            **kwargs: Дополнительные аргументы.

        Returns:
            True если доступ разрешен.

        Raises:
            CancelHandler: Если доступ запрещен (без отправки сообщения).
        """
        # Проверяем пользователя
        if user is None or not user.is_casino_allowed:
            raise CancelHandler()

        # Проверяем группу
        try:
            group = await stp_repo.group.get_groups(message.chat.id)
            if not group or not group.is_casino_allowed:
                raise CancelHandler()
        except Exception:
            # Если ошибка при получении группы - запрещаем доступ
            raise CancelHandler()

        return True
