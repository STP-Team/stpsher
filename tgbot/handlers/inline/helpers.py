#
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
    "EXCHANGE_DETAILS": 5 if _IS_DEVELOPMENT else 30,  # Кеш информации о сделке
    "MY_EXCHANGES": 5 if _IS_DEVELOPMENT else 30,  # Кеш информации об активных сделках
    "SUBSCRIPTION_DETAILS": 5 if _IS_DEVELOPMENT else 30,  # Кеш информации о подписке
}

# Role mappings will be imported from misc modules

EXCHANGE_TYPE_NAMES = {
    "buy": "Покупка часов",
    "sell": "Продажа часов",
    "both": "Оба типа",
}

# Search filter keywords
FILTER_KEYWORDS = {
    "DIVISION": "div",
    "ROLE": "role",
    "POSITION": "pos",
    "USERNAME": "username",
    "USER_ID": "user_id",
}
