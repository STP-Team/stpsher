import logging
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from tgbot.config import load_config
from tgbot.services.logger import setup_logging

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


async def send_email(
    to_addrs: list[str] | str, subject: str, body: str, html: bool = True
):
    """
    Отправка email

    Args:
        to_addrs: Список адресов для отправки письма
        subject: Заголовок письма
        body: Тело письма
        html: Использовать ли HTML для форматирования
    """
    context = ssl.create_default_context()

    msg = MIMEMultipart()
    msg["From"] = config.mail.user
    msg["To"] = ", ".join(to_addrs) if type(to_addrs) is list[str] else to_addrs  #
    msg["Subject"] = Header(subject, "utf-8")

    content_type = "html" if html else "plain"
    msg.attach(MIMEText(body, content_type, "utf-8"))

    try:
        with smtplib.SMTP_SSL(
            host=config.mail.host, port=config.mail.port, context=context
        ) as server:
            server.login(user=config.mail.user, password=config.mail.password)
            server.sendmail(
                from_addr=config.mail.user, to_addrs=to_addrs, msg=msg.as_string()
            )
    except smtplib.SMTPException as e:
        logger.error(f"[Email] Ошибка отправки письма: {e}")


async def send_auth_email(code: str, email: str, bot_username: str):
    email_subject = "Авторизация в боте"
    email_content = f"""Добрый день<br><br>
    
Код для авторизации: <b>{code}</b><br>
Введите код в бота @{bot_username} для завершения авторизации"""

    await send_email(to_addrs=email, subject=email_subject, body=email_content)
    logger.info(
        f"[Авторизация] Письмо с кодом авторизации {code} отправлено на {email}"
    )
