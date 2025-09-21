from aiogram.filters import BaseFilter
from aiogram.types import Message

from infrastructure.database.models import Employee
from tgbot.misc.helpers import get_role


class RootFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="root", return_id=True)


class MipFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="МИП", return_id=True)


class DutyFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="Дежурный", return_id=True)


class GokFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="ГОК", return_id=True)


class HeadFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="Руководитель", return_id=True)


class AdministratorFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="Администратор", return_id=True)


class SpecialistFilter(BaseFilter):
    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        if user is None:
            return False

        return user.role == get_role(role_name="Специалист", return_id=True)


class MultiRoleFilter(BaseFilter):
    def __init__(self, *role_filters):
        self.role_filters = role_filters

    async def __call__(self, obj, **kwargs) -> bool:
        for role_filter in self.role_filters:
            if await role_filter(obj, **kwargs):
                return True
        return False
