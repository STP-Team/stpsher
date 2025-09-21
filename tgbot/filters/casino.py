from aiogram.enums import ParseMode
from aiogram.filters import BaseFilter
from aiogram.types import Message
from marshmallow.fields import Boolean

from infrastructure.database.models import Employee


class IsCasinoAllowed(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool | Boolean:
        if user is None:
            return False

        await obj.answer(
            """❌ Доступ к казино закрыт

Если считаешь, что это ошибка - обратись к своему руководителю""",
            show_alert=True,
            parse_mode=ParseMode.HTML,
        )
        return user.is_casino_allowed
