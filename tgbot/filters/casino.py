"""Фильтры для казино."""

from aiogram.dispatcher.event.bases import CancelHandler
from aiogram.filters import BaseFilter
from aiogram.types import Message
from stp_database.models.STP import Employee


class IsCasinoAllowed(BaseFilter):
    """Фильтр проверки доступа к казино.

    Проверяет имеет ли пользователь право доступа к функционалу казино.
    При отсутствии доступа отправляет сообщение об ошибке и прерывает обработку.
    """

    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        """Проверяет разрешен ли доступ к казино для пользователя.

        Args:
            obj: Входящее сообщение.
            user: Экземпляр пользователя с моделью Employee
            **kwargs: Дополнительные аргументы.

        Returns:
            True если доступ разрешен.

        Raises:
            CancelHandler: Если доступ запрещен (после отправки сообщения об ошибке).
        """
        if user is None or not user.is_casino_allowed:
            await obj.answer(
                """❌ Доступ к казино закрыт

Если считаешь, что это ошибка — обратись к своему руководителю""",
            )
            raise CancelHandler()
        return True
