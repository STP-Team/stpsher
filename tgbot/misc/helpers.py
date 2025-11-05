"""Функции-помощники для основного кода."""

import os
import random
import string

import pytz
from stp_database import Employee

from tgbot.misc.dicts import roles, russian_weekdays_short

IS_DEVELOPMENT = os.getenv("ENVIRONMENT", "production").lower() in (
    "development",
    "dev",
    "debug",
)

tz = pytz.timezone("Asia/Yekaterinburg")
strftime_date = "%H:%M %d.%m.%Y"

# Convert 0-6 indexing from russian_weekdays_short to 1-7 indexing for compatibility
DAY_NAMES = {i + 1: day for i, day in russian_weekdays_short.items()}

# Role mappings from dicts.py structure
ROLE_MAPPINGS = {
    "EMPLOYEE": 1,  # Специалист
    "HEAD": 2,  # Руководитель
    "DUTY": 3,  # Дежурный
    "ADMIN": 4,  # Администратор
    "GOK": 5,  # ГОК
    "MIP": 6,  # МИП
    "ROOT": 10,  # root
}

# Role names from dicts.py
ROLE_NAMES = {role_id: role_data["name"] for role_id, role_data in roles.items()}

# Role aliases for search and lookup
ROLE_ALIASES = {
    "head": ROLE_MAPPINGS["HEAD"],
    "руководитель": ROLE_MAPPINGS["HEAD"],
    "admin": ROLE_MAPPINGS["ADMIN"],
    "администратор": ROLE_MAPPINGS["ADMIN"],
    "user": ROLE_MAPPINGS["EMPLOYEE"],
    "пользователь": ROLE_MAPPINGS["EMPLOYEE"],
    "сотрудник": ROLE_MAPPINGS["EMPLOYEE"],
    "специалист": ROLE_MAPPINGS["EMPLOYEE"],
    "duty": ROLE_MAPPINGS["DUTY"],
    "дежурный": ROLE_MAPPINGS["DUTY"],
    "gok": ROLE_MAPPINGS["GOK"],
    "гок": ROLE_MAPPINGS["GOK"],
    "mip": ROLE_MAPPINGS["MIP"],
    "мип": ROLE_MAPPINGS["MIP"],
    "root": ROLE_MAPPINGS["ROOT"],
}


def generate_auth_code(length=6):
    """Генератор кодов авторизации.

    Args:
        length: Длина кода

    Returns:
        Код авторизации
    """
    chars = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return "".join(random.choice(chars) for _ in range(length))


def get_role(role_id: int = None, role_name: str = None, return_id: bool = False):
    """Получает информацию о роли.

    Args:
        role_id: Идентификатор роли
        role_name: Название роли
        return_id: Нужно ли возвращать идентификатор

    Returns:
        Название и эмодзи роли или идентификатор роли
    """
    if role_id is not None:
        return role_id if return_id else roles.get(role_id)

    if role_name is not None:
        for r_id, data in roles.items():
            if data["name"] == role_name:
                return r_id if return_id else data

    return None


def get_status_emoji(status: str) -> str:
    """Получает эмодзи в зависимости от статуса предмета.

    Args:
        status: Статус предмета

    Returns:
        Эмодзи, отображающий текущий статус предмета
    """
    status_emojis = {
        "stored": "📦",
        "review": "⏳",
        "used_up": "🔒",
    }
    return status_emojis.get(status, "❓")


def get_gender_emoji(name: str) -> str:
    """Определяет пол по имени.

    Args:
        name: Полные ФИО

    Returns:
        Эмодзи гендера
    """
    parts = name.split()
    if len(parts) >= 3:
        patronymic = parts[2]
        if patronymic.endswith("на"):
            return "👩‍💼"
        elif patronymic.endswith(("ич", "ович", "евич")):
            return "👨‍💼"
    return "👨‍💼"


def short_name(full_name: str) -> str:
    """Достает фамилию и имя из ФИО.

    Args:
        full_name: Полные ФИО

    Returns:
        Фамилия и имя
    """
    clean_name = full_name.split("(")[0].strip()
    parts = clean_name.split()

    if len(parts) >= 2:
        return " ".join(parts[:2])
    return clean_name


def format_fullname(
    user: Employee,
    short: bool = True,
    gender_emoji: bool = False,
) -> str:
    """Форматирует ФИО пользователя.

    Args:
        user: Экземпляр пользователя с моделью Employee
        short: Нужно ли сократить до ФИ
        gender_emoji: Нужно ли добавлять эмодзи гендеры к ФИО

    Returns:
        Форматированная строка с указанными параметрами
    """
    if short:
        formatted_fullname = short_name(user.fullname)
    else:
        formatted_fullname = user.fullname

    if user.username is not None:
        formatted_fullname = f"<a href='t.me/{user.username}'>{formatted_fullname}</a>"
    elif user.username is None and user.user_id is not None:
        formatted_fullname = (
            f"<a href='tg://user?id={user.user_id}'>{formatted_fullname}</a>"
        )

    if gender_emoji:
        emoji = get_gender_emoji(user.fullname)
        formatted_fullname = f"{emoji} {formatted_fullname}"

    return formatted_fullname
