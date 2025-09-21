from aiogram.filters import BaseFilter
from aiogram.types import Message

from infrastructure.database.models import Employee
from tgbot.misc.helpers import get_role


class RootFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="root")


class MipFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="МИП")


class DutyFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="Дежурный")


class GokFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="ГОК")


class HeadFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="Руководитель")


class AdministratorFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="Администратор")


class SpecialistFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="Специалист")


class MultiRoleFilter(BaseFilter):
    def __init__(self, *role_filters):
        self.role_filters = role_filters

    async def __call__(self, obj, **kwargs) -> bool:
        for role_filter in self.role_filters:
            if await role_filter(obj, **kwargs):
                return True
        return False
