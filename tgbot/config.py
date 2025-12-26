"""Файл конфигурации проекта."""

from dataclasses import dataclass
from typing import Optional

from environs import Env
from sqlalchemy import URL


@dataclass
class TgBot:
    """Класс конфигурации бота Telegram.

    Attributes:
        environment: Адрес сервера (prod или dev)
        token: Токен бота от @BotFather

        use_redis: Использовать ли Redis

        use_webhook: Использовать ли вебхуки
        webhook_domain: Домен вебхука
        webhook_path: Кастомный путь к вебхуку
        webhook_secret: Секретный токен вебхука
        webhook_port: Порт вебхука
    """

    environment: str
    token: str
    use_redis: bool
    use_webhook: bool
    webhook_domain: Optional[str] = None
    webhook_path: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_port: int = 8443

    @staticmethod
    def from_env(env: Env):
        """Создает объект TgBot из переменных окружения.

        Args:
            env: Объект переменных окружения

        Returns:
            Собранный объект TgBot
        """
        environment = env.str("ENVIRONMENT")
        token = env.str("BOT_TOKEN")
        use_redis = env.bool("USE_REDIS")
        use_webhook = env.bool("USE_WEBHOOK", False)
        webhook_domain = env.str("WEBHOOK_DOMAIN", None)
        webhook_path = env.str("WEBHOOK_PATH", "/stpsher")
        webhook_secret = env.str("WEBHOOK_SECRET", None)
        webhook_port = env.int("WEBHOOK_PORT", 8443)

        return TgBot(
            environment=environment,
            token=token,
            use_redis=use_redis,
            use_webhook=use_webhook,
            webhook_domain=webhook_domain,
            webhook_path=webhook_path,
            webhook_secret=webhook_secret,
            webhook_port=webhook_port,
        )


@dataclass
class DbConfig:
    """Класс конфигурации подключения к базам данных.

    Attributes:
        host: Адрес сервера
        user: Логин пользователя БД
        password: Пароль пользователя БД

        stp_db: Название базы данных STP
        stats_db: Название базы данных KPI
    """

    host: str
    user: str
    password: str

    stp_db: str
    stats_db: str

    def construct_sqlalchemy_url(
        self,
        db_name=None,
        driver="aiomysql",
    ) -> URL:
        """Собирает строку SQLAlchemy для подключения к MariaDB.

        Args:
            db_name: Название базы данных
            driver: Драйвер для подключения

        Returns:
            Возвращает собранную строку для подключения к базе используя SQLAlchemy
        """
        connection_url = URL.create(
            f"mysql+{driver}",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port if hasattr(self, "port") and self.port else 3306,
            database=db_name,
            query={
                "charset": "utf8mb4",
                "use_unicode": "1",
                "sql_mode": "TRADITIONAL",
                "connect_timeout": "30",
                "autocommit": "false",
            },
        )

        return connection_url

    @staticmethod
    def from_env(env: Env):
        """Создает объект DbConfig из переменных окружения.

        Args:
            env: Объект переменных окружения

        Returns:
            Собранный объект DbConfig
        """
        host = env.str("DB_HOST")
        user = env.str("DB_USER")
        password = env.str("DB_PASS")

        stp_db = env.str("STP_DB_NAME")
        stats_db = env.str("STATS_DB_NAME")

        return DbConfig(
            host=host, user=user, password=password, stp_db=stp_db, stats_db=stats_db
        )


@dataclass
class MailConfig:
    """Класс конфигурации подключения к email-серверу.

    Attributes:
        host: Адрес почтового сервера
        port: Порт почтового сервера
        user: Логин почтового аккаунта
        password: Пароль почтового аккаунта
        use_ssl: Использовать ли флаг use_ssl при подключении
    """

    host: str
    port: int
    user: str
    password: str
    use_ssl: bool

    nck_email_addr: str
    ntp_email_addr: str
    gok_email_addr: str
    mip_email_addr: str

    @staticmethod
    def from_env(env: Env):
        """Создает объект MailConfig из переменных окружения.

        Args:
            env: Объект переменных окружения

        Returns:
            Собранный объект MailConfig
        """
        host = env.str("EMAIL_HOST")
        port = env.int("EMAIL_PORT")
        user = env.str("EMAIL_USER")
        password = env.str("EMAIL_PASS")
        use_ssl = env.bool("EMAIL_USE_SSL")

        nck_email_addr = env.str("NCK_EMAIL_ADDR")
        ntp_email_addr = env.str("NTP_EMAIL_ADDR")
        gok_email_addr = env.str("GOK_EMAIL_ADDR")
        mip_email_addr = env.str("MIP_EMAIL_ADDR")

        return MailConfig(
            host=host,
            port=port,
            user=user,
            password=password,
            use_ssl=use_ssl,
            nck_email_addr=nck_email_addr,
            ntp_email_addr=ntp_email_addr,
            gok_email_addr=gok_email_addr,
            mip_email_addr=mip_email_addr,
        )


@dataclass
class RedisConfig:
    """Класс конфигурации подключения к Redis серверу.

    Attributes:
        redis_host: Адрес Redis сервера
        redis_port: Порт Redis сервера
        redis_pass: Пароль для подключения к Redis
    """

    redis_pass: Optional[str]
    redis_port: Optional[int]
    redis_host: Optional[str]

    def dsn(self) -> str:
        """Собирает строку Redis DSN (Data Source Name) для подключения к Redis.

        Returns:
            Возвращает собранную строку для подключения к Redis
        """
        if self.redis_pass:
            return f"redis://:{self.redis_pass}@{self.redis_host}:{self.redis_port}/0"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/0"

    @staticmethod
    def from_env(env: Env):
        """Создает объект RedisConfig из переменных окружения.

        Args:
            env: Объект переменных окружения

        Returns:
            Собранный объект RedisConfig
        """
        redis_pass = env.str("REDIS_PASSWORD")
        redis_port = env.int("REDIS_PORT")
        redis_host = env.str("REDIS_HOST")

        return RedisConfig(
            redis_pass=redis_pass, redis_port=redis_port, redis_host=redis_host
        )


@dataclass
class Config:
    """Основной класс конфигурации.

    Этот класс содержит все остальные классы конфигурации, предоставляя централизованный доступ ко всем настройкам.

    Attributes:
    ----------
    tg_bot: Содержит настройки Telegram бота
    mail: Содержит настройки почтового сервера
    db: Содержит настройки подключения к базе данных
    redis: Содержит настройки подключения к Redis
    """

    tg_bot: TgBot
    mail: MailConfig
    db: Optional[DbConfig]
    redis: Optional[RedisConfig]


def load_config(path: str = None) -> Config:
    """Загружает конфиг из переменных окружения.

    Читает либо значения из файла .env, если предоставлен путь до него, иначе читает из переменных запущенного процесса.

    Args:
        path: Опциональный путь к файлу переменных окружения

    Returns:
        Объект Config с аттрибутами для каждого класса конфигурации
    """
    env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot.from_env(env),
        mail=MailConfig.from_env(env),
        db=DbConfig.from_env(env),
        redis=RedisConfig.from_env(env),
    )


# Глобальная конфигурация для определения окружения
_global_config = load_config(".env")
IS_DEVELOPMENT = _global_config.tg_bot.environment == "dev"
