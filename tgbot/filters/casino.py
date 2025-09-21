from aiogram.dispatcher.event.bases import CancelHandler
from aiogram.enums import ParseMode
from aiogram.filters import BaseFilter
from aiogram.types import Message

from infrastructure.database.models import Employee


class IsCasinoAllowed(BaseFilter):
    async def __call__(self, obj: Message, user: "Employee", **kwargs) -> bool:
        if user is None or not user.is_casino_allowed:
            await obj.answer(
                """❌ Доступ к казино закрыт

Если считаешь, что это ошибка — обратись к своему руководителю""",
                parse_mode=ParseMode.HTML,
            )
            raise CancelHandler()
        return True
