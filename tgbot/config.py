from dataclasses import dataclass
from typing import Optional

from environs import Env
from sqlalchemy import URL


@dataclass
class DbConfig:
    """
    Database configuration class.
    This class holds the settings for the database, such as host, password, port, etc.

    Attributes
    ----------
    host : str
        Хост, на котором находится база данных
    password : str
        Пароль для авторизации в базе данных.
    user : str
        Логин для авторизации в базе данных.
    stp_db : str
        Имя основной базы данных.
    achievements_db : str
        Имя базы данных достижений.
    """

    host: str
    user: str
    password: str

    stp_db: str
    achievements_db: str

    def construct_sqlalchemy_url(
        self,
        db_name=None,
        driver="aioodbc",
    ) -> URL:
        """
        Конструирует и возвращает SQLAlchemy-ссылку для подключения к базе данных
        """
        connection_string = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={self.host};"
            f"DATABASE={db_name if db_name else self.achievements_db};"
            f"UID={self.user};"
            f"PWD={self.password};"
            f"TrustServerCertificate=yes;"
            f"MultipleActiveResultSets=yes;"
            f"MARS_Connection=yes;"
            f"Connection Timeout=30;"
            f"Command Timeout=60;"
            f"Pooling=yes;"
            f"Max Pool Size=100;"
            f"Min Pool Size=5;"
            f"TCP KeepAlive=yes;"
            f"ConnectRetryCount=3;"
            f"ConnectRetryInterval=10;"
        )
        connection_url = URL.create(
            f"mssql+{driver}", query={"odbc_connect": connection_string}
        )

        return connection_url

    @staticmethod
    def from_env(env: Env):
        """
        Creates the DbConfig object from environment variables.
        """
        host = env.str("DB_HOST")
        user = env.str("DB_USER")
        password = env.str("DB_PASS")

        stp_db = env.str("DB_STP_NAME")
        achievements_db = env.str("DB_ACHIEVEMENTS_NAME")

        return DbConfig(
            host=host,
            user=user,
            password=password,
            stp_db=stp_db,
            achievements_db=achievements_db,
        )


@dataclass
class TgBot:
    """
    Creates the TgBot object from environment variables.
    """

    token: str
    use_redis: bool

    @staticmethod
    def from_env(env: Env):
        """
        Creates the TgBot object from environment variables.
        """
        token = env.str("BOT_TOKEN")
        use_redis = env.bool("USE_REDIS")
        return TgBot(token=token, use_redis=use_redis)


@dataclass
class RedisConfig:
    """
    Redis configuration class.

    Attributes
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
        """
        Constructs and returns a Redis DSN (Data Source Name) for this database configuration.
        """
        if self.redis_pass:
            return f"redis://:{self.redis_pass}@{self.redis_host}:{self.redis_port}/0"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/0"

    @staticmethod
    def from_env(env: Env):
        """
        Creates the RedisConfig object from environment variables.
        """
        redis_pass = env.str("REDIS_PASSWORD")
        redis_port = env.int("REDIS_PORT")
        redis_host = env.str("REDIS_HOST")

        return RedisConfig(
            redis_pass=redis_pass, redis_port=redis_port, redis_host=redis_host
        )


@dataclass
class Miscellaneous:
    """
    Miscellaneous configuration class.

    This class holds settings for various other parameters.
    It merely serves as a placeholder for settings that are not part of other categories.

    Attributes
    ----------
    other_params : str, optional
        A string used to hold other various parameters as required (default is None).
    """

    other_params: str = None


@dataclass
class Config:
    """
    The main configuration class that integrates all the other configuration classes.

    This class holds the other configuration classes, providing a centralized point of access for all settings.

    Attributes
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
    misc: Miscellaneous
    db: Optional[DbConfig] = None
    redis: Optional[RedisConfig] = None


def load_config(path: str = None) -> Config:
    """
    This function takes an optional file path as input and returns a Config object.
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
        db=DbConfig.from_env(env),
        redis=RedisConfig.from_env(env),
        misc=Miscellaneous(),
    )
