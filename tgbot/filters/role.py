from aiogram.filters import BaseFilter
from aiogram.types import Message

from infrastructure.database.models.STP.employee import Employee
from tgbot.misc.dicts import executed_codes


class RootFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["root"]


class MipFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["МИП"]


class DutyFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["Дежурный"]


class GokFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["ГОК"]


class HeadFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["Руководитель"]


class AdministratorFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["Администратор"]


class SpecialistFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == executed_codes["Специалист"]


class MultiRoleFilter(BaseFilter):
    def __init__(self, *role_filters):
        self.role_filters = role_filters

    async def __call__(self, obj, **kwargs) -> bool:
        for role_filter in self.role_filters:
            if await role_filter(obj, **kwargs):
                return True
        return False
