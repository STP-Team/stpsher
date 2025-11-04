# Constants
import os

SEARCH_LIMITS = {
    "MAX_FIO_SEARCH": 50,
    "DEFAULT_LIMIT": 20,
    "INLINE_RESULTS": 15,
    "MAX_DISPLAY_RESULTS": 12,
}

# Cache time settings - use environment variable to switch between dev/prod
_IS_DEVELOPMENT = os.getenv("ENVIRONMENT", "production").lower() in (
    "development",
    "dev",
    "debug",
)

CACHE_TIMES = {
    "DEFAULT_COMMANDS": 3 if _IS_DEVELOPMENT else 60,
    "SEARCH_RESULTS": 3 if _IS_DEVELOPMENT else 300,
    "NO_CACHE": 0,
    "EXCHANGE_DETAILS": 5 if _IS_DEVELOPMENT else 180,  # Cache exchange details
    "SUBSCRIPTION_DETAILS": 5 if _IS_DEVELOPMENT else 300,  # Cache subscription details
}

ROLE_MAPPINGS = {
    "EMPLOYEE": 1,
    "HEAD": 2,
    "ADMIN": 3,
}

ROLE_NAMES = {
    1: "сотрудник",
    2: "руководитель",
    3: "администратор",
}

EXCHANGE_TYPE_NAMES = {
    "buy": "Покупка часов",
    "sell": "Продажа часов",
    "both": "Оба типа",
}

DAY_NAMES = {
    1: "Пн",
    2: "Вт",
    3: "Ср",
    4: "Чт",
    5: "Пт",
    6: "Сб",
    7: "Вс",
}


# Search filter keywords
FILTER_KEYWORDS = {
    "DIVISION": "div",
    "ROLE": "role",
    "POSITION": "pos",
    "USERNAME": "username",
    "USER_ID": "user_id",
}

ROLE_ALIASES = {
    "head": ROLE_MAPPINGS["HEAD"],
    "руководитель": ROLE_MAPPINGS["HEAD"],
    "admin": ROLE_MAPPINGS["ADMIN"],
    "администратор": ROLE_MAPPINGS["ADMIN"],
    "user": ROLE_MAPPINGS["EMPLOYEE"],
    "пользователь": ROLE_MAPPINGS["EMPLOYEE"],
    "сотрудник": ROLE_MAPPINGS["EMPLOYEE"],
}
