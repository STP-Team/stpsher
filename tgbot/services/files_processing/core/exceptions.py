"""Пользовательские исключения для обработки расписаний."""


class ScheduleError(Exception):
    """Базовое исключение для ошибок, связанных с расписанием."""

    pass


class ScheduleFileNotFoundError(ScheduleError):
    """Исключение, возникающее когда файл расписания не найден."""

    pass


class UserNotFoundError(ScheduleError):
    """Исключение, возникающее когда пользователь не найден в расписании."""

    pass


class MonthNotFoundError(ScheduleError):
    """Исключение, возникающее когда месяц не найден в расписании."""

    pass


class InvalidDataError(ScheduleError):
    """Исключение, возникающее когда данные расписания неверны или повреждены."""

    pass
