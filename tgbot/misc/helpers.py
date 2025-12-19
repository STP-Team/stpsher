"""Функции-помощники для основного кода."""

import calendar
import random
import string
from datetime import date

import pytz
from stp_database.models.STP import Employee

from tgbot.misc.dicts import roles, russian_weekdays_short

tz_perm = pytz.timezone("Asia/Yekaterinburg")
tz_moscow = pytz.timezone("Europe/Moscow")
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
    user: Employee = None,
    short: bool = True,
    gender_emoji: bool = False,
    fullname: str = None,
    username: str = None,
    user_id: int = None,
) -> str:
    """Форматирует ФИО пользователя.

    Args:
        user: Экземпляр пользователя с моделью Employee
        short: Нужно ли сократить до ФИ
        gender_emoji: Нужно ли добавлять эмодзи гендеры к ФИО
        fullname: ФИО пользователя (используется когда user=None)
        username: Username пользователя (используется когда user=None)
        user_id: ID пользователя (используется когда user=None)

    Returns:
        Форматированная строка с указанными параметрами
    """
    # Определяем источник данных
    if user is not None:
        # Используем данные из объекта Employee
        user_fullname = user.fullname
        user_username = user.username
        user_user_id = user.user_id
    else:
        # Используем переданные параметры
        user_fullname = fullname or ""
        user_username = username
        user_user_id = user_id

    # Форматируем ФИО
    if short and user_fullname:
        formatted_fullname = short_name(user_fullname)
    else:
        formatted_fullname = user_fullname

    # Добавляем ссылку, если есть username или user_id
    if user_username is not None:
        formatted_fullname = f"<a href='t.me/{user_username}'>{formatted_fullname}</a>"
    elif user_username is None and user_user_id is not None:
        formatted_fullname = (
            f"<a href='tg://user?id={user_user_id}'>{formatted_fullname}</a>"
        )

    # Добавляем эмодзи гендера, если требуется
    if gender_emoji and user_fullname:
        emoji = get_gender_emoji(user_fullname)
        formatted_fullname = f"{emoji} {formatted_fullname}"

    return formatted_fullname


async def get_random_currency():
    currencies = [
        "фантиков",
        "морковок",
        "пылинок",
        "крекеров",
        "носков",
        "семечек",
        "кубиков",
        "воплей",
        "коней",
        "скрепок",
        "бубликов",
        "котлет",
        "зефирок",
        "гвоздиков",
        "крошек",
        "тыквочек",
        "червячков",
        "батареек",
        "огурчиков",
        "лепестков",
        "шестерёнок",
        "тапочков",
        "монеток",
        "пончиков",
        "пельмешков",
        "пузырьков",
        "печенек",
        "корочек",
        "стружек",
        "кирпичиков",
        "букашек",
        "клякс",
        "пикселей",
        "лапшей",
        "карандашей",
        "проводков",
        "лампочек",
        "ключиков",
        "чашек",
        "тарелочек",
        "кнопочек",
        "складочек",
        "фантомов",
        "сушек",
        "камешков",
        "листочков",
        "пружинок",
        "конфеток",
        "ягодок",
        "шишек",
        "мешочков",
        "винтиков",
        "духов",
        "капелек",
        "ворсинок",
        "кексиков",
        "бусинок",
        "фонариков",
        "петель",
        "звоночков",
        "кактусиков",
        "полосочек",
        "монолитиков",
        "ступенек",
        "блёсток",
        "шлейфов",
        "коробочек",
        "усиков",
        "завитков",
        "стеклышек",
        "слоников",
        "горошин",
        "ложечек",
        "веточек",
        "лепёшек",
        "палочек",
        "бочонков",
        "шоколадок",
        "рыбёшек",
        "зубчиков",
        "одёжек",
        "лент",
        "мякишей",
        "хлопьев",
        "камышинок",
        "узелков",
        "медузок",
        "облачков",
        "сочней",
        "чулочков",
        "чернил",
        "крылышек",
        "пупырок",
        "баночек",
        "горошков",
    ]
    return random.choice(currencies)


def format_currency_price(
    price: float, total_price: float, use_random_currency: bool = False
) -> str:
    """Форматирует цену с соответствующей валютой.

    Args:
        price: Цена за час
        total_price: Общая цена
        use_random_currency: Использовать случайную валюту вместо рублей

    Returns:
        Форматированная строка цены
    """
    if use_random_currency:
        currency = random.choice([
            "фантиков",
            "морковок",
            "пылинок",
            "крекеров",
            "носков",
            "семечек",
            "кубиков",
            "воплей",
            "коней",
            "скрепок",
            "бубликов",
            "котлет",
            "зефирок",
            "гвоздиков",
            "крошек",
            "тыквочек",
            "червячков",
            "батареек",
            "огурчиков",
            "лепестков",
            "шестерёнок",
            "тапочков",
            "монеток",
            "пончиков",
        ])
        return f"{price:g} {currency}/ч. ({total_price:g} {currency})"
    else:
        return f"{price:g} ₽/ч. ({total_price:g} ₽)"


def calculate_age(birthday):
    """Вычисляет возраст на основе даты рождения.

    Args:
        birthday: Дата рождения (строка в формате DD.MM.YYYY)

    Returns:
        str: Возраст с правильным склонением (например, "32 года"), или None если дата невалидна
    """
    if not birthday:
        return None

    try:
        # Парсим дату в формате DD.MM.YYYY
        if isinstance(birthday, str):
            day, month, year = birthday.split(".")
            birthday = date(int(year), int(month), int(day))
        elif hasattr(birthday, "date"):
            birthday = birthday.date()

        today = date.today()
        age = today.year - birthday.year

        # Корректируем возраст, если день рождения ещё не наступил в этом году
        if (today.month, today.day) < (birthday.month, birthday.day):
            age -= 1

        # Правильное склонение для возраста
        if age % 10 == 1 and age % 100 != 11:
            return f"{age} год"
        elif age % 10 in [2, 3, 4] and age % 100 not in [12, 13, 14]:
            return f"{age} года"
        else:
            return f"{age} лет"

    except (ValueError, AttributeError):
        return None


def calculate_work_experience(employment_date):
    """Вычисляет стаж работы на основе даты трудоустройства.

    Args:
        employment_date: Дата трудоустройства (строка в формате DD.MM.YYYY)

    Returns:
        str: Стаж в виде "X лет Y месяцев Z дней" или None если дата невалидна
    """
    if not employment_date:
        return None

    try:
        # Парсим дату в формате DD.MM.YYYY
        if isinstance(employment_date, str):
            day, month, year = employment_date.split(".")
            emp_date = date(int(year), int(month), int(day))
        elif hasattr(employment_date, "date"):
            emp_date = employment_date.date()
        else:
            emp_date = employment_date

        today = date.today()

        # Вычисляем разность
        years = today.year - emp_date.year
        months = today.month - emp_date.month
        days = today.day - emp_date.day

        # Корректируем, если текущий день меньше дня трудоустройства
        if days < 0:
            months -= 1
            # Получаем количество дней в предыдущем месяце
            if today.month == 1:
                prev_month_days = calendar.monthrange(today.year - 1, 12)[1]
            else:
                prev_month_days = calendar.monthrange(today.year, today.month - 1)[1]
            days += prev_month_days

        # Корректируем, если текущий месяц меньше месяца трудоустройства
        if months < 0:
            years -= 1
            months += 12

        # Форматируем результат
        parts = []
        if years > 0:
            if years == 1:
                parts.append("1 год")
            elif 2 <= years <= 4:
                parts.append(f"{years} года")
            else:
                parts.append(f"{years} лет")

        if months > 0:
            if months == 1:
                parts.append("1 месяц")
            elif 2 <= months <= 4:
                parts.append(f"{months} месяца")
            else:
                parts.append(f"{months} месяцев")

        if (
            days > 0 and len(parts) < 2
        ):  # Показываем дни только если нет и лет, и месяцев
            if days == 1:
                parts.append("1 день")
            elif 2 <= days <= 4:
                parts.append(f"{days} дня")
            else:
                parts.append(f"{days} дней")

        if not parts:
            return "меньше дня"

        return " ".join(parts)

    except (ValueError, AttributeError):
        return None
