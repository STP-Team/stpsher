from dataclasses import dataclass
from typing import Optional

from environs import Env
from sqlalchemy import URL


@dataclass
class TgBot:
    """Creates the TgBot object from environment variables."""

    token: str
    use_redis: bool
    use_webhook: bool
    webhook_domain: Optional[str] = None
    webhook_path: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_port: int = 8443

    @staticmethod
    def from_env(env: Env):
        """Creates the TgBot object from environment variables."""
        token = env.str("BOT_TOKEN")
        use_redis = env.bool("USE_REDIS")
        use_webhook = env.bool("USE_WEBHOOK", False)
        webhook_domain = env.str("WEBHOOK_DOMAIN", None)
        webhook_path = env.str("WEBHOOK_PATH", "/webhook")
        webhook_secret = env.str("WEBHOOK_SECRET", None)
        webhook_port = env.int("WEBHOOK_PORT", 8443)

        return TgBot(
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
    """Database configuration class.
    This class holds the settings for the database, such as host, password, port, etc.

    Attributes:
    ----------
    host : str
        Хост, на котором находится база данных
    password : str
        Пароль для авторизации в базе данных.
    user : str
        Логин для авторизации в базе данных.
    main_db : str
        Имя основной базы данных.
    kpi_db : str
        Имя основной базы данных.
    """

    host: str
    user: str
    password: str

    main_db: str
    kpi_db: str

    def construct_sqlalchemy_url(
        self,
        db_name=None,
        driver="aiomysql",
    ) -> URL:
        """Constructs and returns SQLAlchemy URL for MariaDB database connection"""
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
        """Creates the DbConfig object from environment variables."""
        host = env.str("DB_HOST")
        user = env.str("DB_USER")
        password = env.str("DB_PASS")

        main_db = env.str("MAIN_DB_NAME")
        kpi_db = env.str("KPI_DB_NAME")

        return DbConfig(
            host=host, user=user, password=password, main_db=main_db, kpi_db=kpi_db
        )


@dataclass
class MailConfig:
    """Creates the Email object from environment variables.

    Attributes:
    ----------
    host : str
        The host where the email server is located.
    port : int
        The port which used to connect to the email server.
    user : str
        The username used to authenticate with the email server.
    password : str
        The password used to authenticate with the email server.
    use_ssl : bool
        The use_ssl flag used to connect to the email server.
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
        """Creates the Email object from environment variables."""
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
    """Redis configuration class.

    Attributes:
    ----------
    redis_pass : Optional(str)
        The password used to authenticate with Redis.
    redis_port : Optional(int)
        The port where Redis server is listening.
    redis_host : Optional(str)
        The host where Redis server is located.
    """

    redis_pass: Optional[str]
    redis_port: Optional[int]
    redis_host: Optional[str]

    def dsn(self) -> str:
        """Constructs and returns a Redis DSN (Data Source Name) for this database configuration."""
        if self.redis_pass:
            return f"redis://:{self.redis_pass}@{self.redis_host}:{self.redis_port}/0"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/0"

    @staticmethod
    def from_env(env: Env):
        """Creates the RedisConfig object from environment variables."""
        redis_pass = env.str("REDIS_PASSWORD")
        redis_port = env.int("REDIS_PORT")
        redis_host = env.str("REDIS_HOST")

        return RedisConfig(
            redis_pass=redis_pass, redis_port=redis_port, redis_host=redis_host
        )


@dataclass
class Miscellaneous:
    """Miscellaneous configuration class.

    This class holds settings for various other parameters.
    It merely serves as a placeholder for settings that are not part of other categories.

    Attributes:
    ----------
    other_params : str, optional
        A string used to hold other various parameters as required (default is None).
    """

    other_params: str = None


@dataclass
class Config:
    """The main configuration class that integrates all the other configuration classes.

    This class holds the other configuration classes, providing a centralized point of access for all settings.

    Attributes:
    ----------
    tg_bot : TgBot
        Holds the settings related to the Telegram Bot.
    misc : Miscellaneous
        Holds the values for miscellaneous settings.
    db : Optional[DbConfig]
        Holds the settings specific to the database (default is None).
    redis : Optional[RedisConfig]
        Holds the settings specific to Redis (default is None).
    """

    tg_bot: TgBot
    mail: MailConfig
    misc: Miscellaneous
    db: Optional[DbConfig] = None
    redis: Optional[RedisConfig] = None


def load_config(path: str = None) -> Config:
    """This function takes an optional file path as input and returns a Config object.
    :param path: The path of env file from where to load the configuration variables.
    It reads environment variables from a .env file if provided, else from the process environment.
    :return: Config object with attributes set as per environment variables.
    """
    # Create an Env object.
    # The Env object will be used to read environment variables.
    env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot.from_env(env),
        mail=MailConfig.from_env(env),
        db=DbConfig.from_env(env),
        redis=RedisConfig.from_env(env),
        misc=Miscellaneous(),
    )
