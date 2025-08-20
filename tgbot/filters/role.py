from aiogram.filters import BaseFilter
from aiogram.types import Message

from infrastructure.database.models.user import User
from tgbot.misc.dicts import executed_codes


class RootFilter(BaseFilter):
    async def __call__(self, obj: Message, user: User, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["root"]


class MipFilter(BaseFilter):
    async def __call__(self, obj: Message, user: User, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["МИП"]


class DutyFilter(BaseFilter):
    async def __call__(self, obj: Message, user: User, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["Старший"]


class GokFilter(BaseFilter):
    async def __call__(self, obj: Message, user: User, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["ГОК"]


class HeadFilter(BaseFilter):
    async def __call__(self, obj: Message, user: User, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["Руководитель"]


class AdministratorFilter(BaseFilter):
    async def __call__(self, obj: Message, user: User, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["Администратор"]


class SpecialistFilter(BaseFilter):
    async def __call__(self, obj: Message, user: User, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["Специалист"]
