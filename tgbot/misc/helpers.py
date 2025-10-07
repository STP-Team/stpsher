import random
import string

from tgbot.misc.dicts import roles


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
    fullname: str,
    short: bool = True,
    gender_emoji: bool = False,
    username: str = None,
    user_id: int = None,
) -> str:
    """Форматирует ФИО пользователя.

    Args:
        fullname: Полные ФИО
        short: Нужно ли сократить до ФИ
        gender_emoji: Нужно ли добавлять эмодзи гендеры к ФИО
        username: Юзернейм пользователя Telegram
        user_id: Идентификатор пользователя Telegram

    Returns:
        Форматированная строка с указанными параметрами
    """
    if short:
        formatted_fullname = short_name(fullname)
    else:
        formatted_fullname = fullname

    if username is not None:
        formatted_fullname = f"<a href='t.me/{username}'>{formatted_fullname}</a>"
    elif username is None and user_id is not None:
        formatted_fullname = (
            f"<a href='tg://user?id={user_id}'>{formatted_fullname}</a>"
        )

    if gender_emoji:
        emoji = get_gender_emoji(fullname)
        formatted_fullname = f"{emoji} {formatted_fullname}"

    return formatted_fullname
