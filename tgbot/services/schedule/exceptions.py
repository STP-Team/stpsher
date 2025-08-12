"""
Кастомные исключения при обработке графиков.
"""


class ScheduleError(Exception):
    """Базовое исключение"""

    pass


class ScheduleFileNotFoundError(ScheduleError):
    """Файл графиков не найден"""

    pass


class UserNotFoundError(ScheduleError):
    """Пользователь не найден в графике"""

    pass


class MonthNotFoundError(ScheduleError):
    """Месяц не найден в графике"""

    pass


class InvalidDataError(ScheduleError):
    """Некорректная дата в графике"""

    pass
