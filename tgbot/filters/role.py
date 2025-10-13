"""Фильтры для ролей."""

from aiogram.filters import BaseFilter
from aiogram.types import Message
from stp_database import Employee

from tgbot.misc.helpers import get_role


class RootFilter(BaseFilter):
    """Фильтр проверки роли пользователя Root.

    Проверяет является ли пользователь суперадминистратором системы.
    """

    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        """Проверяет имеет ли пользователь роль root.

        Args:
            obj: Входящее сообщение.
            user: Объект сотрудника из базы данных.
            **kwargs: Дополнительные аргументы.

        Returns:
            True если пользователь имеет роль root, False в противном случае.
        """
        if user is None:
            return False

        return user.role == get_role(role_name="root", return_id=True)


class AdminFilter(BaseFilter):
    """Фильтр проверки роли Администратор.

    Проверяет является ли пользователь администратором.
    """

    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        """Проверяет имеет ли пользователь роль Администратор.

        Args:
            obj: Входящее сообщение.
            user: Объект сотрудника из базы данных.
            **kwargs: Дополнительные аргументы.

        Returns:
            True если пользователь имеет роль Администратор, False в противном случае.
        """
        if user is None:
            return False

        return user.role == get_role(role_name="Администратор", return_id=True)


class GokFilter(BaseFilter):
    """Фильтр проверки роли ГОК.

    Проверяет является ли пользователь сотрудником ГОК (Группа Оперативного Контроля).
    """

    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        """Проверяет имеет ли пользователь роль ГОК.

        Args:
            obj: Входящее сообщение.
            user: Объект сотрудника из базы данных.
            **kwargs: Дополнительные аргументы.

        Returns:
            True если пользователь имеет роль ГОК, False в противном случае.
        """
        if user is None:
            return False

        return user.role == get_role(role_name="ГОК", return_id=True)


class MipFilter(BaseFilter):
    """Фильтр проверки роли МИП.

    Проверяет является ли пользователь сотрудником МИП (Менеджер по Инфраструктуре и Продажам).
    """

    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        """Проверяет имеет ли пользователь роль МИП.

        Args:
            obj: Входящее сообщение.
            user: Объект сотрудника из базы данных.
            **kwargs: Дополнительные аргументы.

        Returns:
            True если пользователь имеет роль МИП, False в противном случае.
        """
        if user is None:
            return False

        return user.role == get_role(role_name="МИП", return_id=True)


class HeadFilter(BaseFilter):
    """Фильтр проверки роли Руководитель.

    Проверяет является ли пользователь руководителем.
    """

    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        """Проверяет имеет ли пользователь роль Руководитель.

        Args:
            obj: Входящее сообщение.
            user: Объект сотрудника из базы данных.
            **kwargs: Дополнительные аргументы.

        Returns:
            True если пользователь имеет роль Руководитель, False в противном случае.
        """
        if user is None:
            return False

        return user.role == get_role(role_name="Руководитель", return_id=True)


class DutyFilter(BaseFilter):
    """Фильтр проверки роли Дежурный.

    Проверяет является ли пользователь дежурным.
    """

    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        """Проверяет имеет ли пользователь роль Дежурный.

        Args:
            obj: Входящее сообщение.
            user: Объект сотрудника из базы данных.
            **kwargs: Дополнительные аргументы.

        Returns:
            True если пользователь имеет роль Дежурный, False в противном случае.
        """
        if user is None:
            return False

        return user.role == get_role(role_name="Дежурный", return_id=True)


class SpecialistFilter(BaseFilter):
    """Фильтр проверки роли Специалист.

    Проверяет является ли пользователь специалистом.
    """

    async def __call__(self, obj: Message, user: Employee, **kwargs) -> bool:
        """Проверяет имеет ли пользователь роль Специалист.

        Args:
            obj: Входящее сообщение.
            user: Объект сотрудника из базы данных.
            **kwargs: Дополнительные аргументы.

        Returns:
            True если пользователь имеет роль Специалист, False в противном случае.
        """
        if user is None:
            return False

        return user.role == get_role(role_name="Специалист", return_id=True)


class MultiRoleFilter(BaseFilter):
    """Фильтр проверки множественных ролей.

    Позволяет проверить пользователя на соответствие любой из переданных ролей.
    Возвращает True если хотя бы одна из ролей подходит.
    """

    def __init__(self, *role_filters):
        """Инициализирует фильтр множественных ролей.

        Args:
            *role_filters: Произвольное количество фильтров ролей для проверки.
        """
        self.role_filters = role_filters

    async def __call__(self, obj, **kwargs) -> bool:
        """Проверяет соответствует ли пользователь хотя бы одной из переданных ролей.

        Args:
            obj: Входящее сообщение.
            **kwargs: Дополнительные аргументы, включая объект пользователя.

        Returns:
            True если пользователь соответствует хотя бы одной роли, False в противном случае.
        """
        for role_filter in self.role_filters:
            if await role_filter(obj, **kwargs):
                return True
        return False
