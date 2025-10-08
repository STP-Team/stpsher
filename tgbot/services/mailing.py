"""Сервис отправки email писем."""

import logging
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from infrastructure.database.models import Employee, Product
from infrastructure.database.models.STP.purchase import Purchase
from tgbot.config import load_config

config = load_config(".env")

logger = logging.getLogger(__name__)


async def send_email(
    addresses: list[str] | str, subject: str, body: str, html: bool = True
) -> None:
    """Отправляет письмо на указанные email.

    Args:
        addresses: Список адресов для отправки письма
        subject: Заголовок письма
        body: Тело письма
        html: Использовать ли HTML для форматирования
    """
    context = ssl.create_default_context()

    msg = MIMEMultipart()
    msg["From"] = config.mail.user
    msg["To"] = ", ".join(addresses) if isinstance(addresses, list) else addresses
    msg["Subject"] = Header(subject, "utf-8")

    content_type = "html" if html else "plain"
    msg.attach(MIMEText(body, content_type, "utf-8"))

    try:
        with smtplib.SMTP_SSL(
            host=config.mail.host, port=config.mail.port, context=context
        ) as server:
            server.login(user=config.mail.user, password=config.mail.password)
            server.sendmail(
                from_addr=config.mail.user, to_addrs=addresses, msg=msg.as_string()
            )
    except smtplib.SMTPException as e:
        logger.error(f"[Email] Ошибка отправки письма: {e}")


async def send_auth_email(code: str, email: str, bot_username: str) -> None:
    """Отправляет письмо с кодом авторизации.

    Args:
        code: Код авторизации
        email: Почта для отправки кода
        bot_username: Юзернейм бота Telegram (для гиперссылки)
    """
    email_subject = "Авторизация в боте"
    email_content = f"""Добрый день<br><br>

Код для авторизации: <b>{code}</b><br>
Введите код в бота <a href="https://t.me/{bot_username}">@{bot_username}</a> для завершения авторизации"""

    await send_email(addresses=email, subject=email_subject, body=email_content)


async def send_activation_product_email(
    user: Employee,
    user_head: Employee | None,
    current_duty: Employee | None,
    product: Product,
    purchase: Purchase,
    bot_username: str,
) -> None:
    """Отправляет письмо с уведомлением об активации предмета.

    Args:
        user: Экземпляр пользователя с моделью Employee. Сотрудник, активировавший предмет
        user_head: Руководитель сотрудника, активировавшего предмет
        current_duty: Текущий дежурный
        product: Активируемый предмет
        purchase: Покупка, в рамках которой был приобретен предмет
        bot_username: Юзернейм бота Telegram
    """
    email_subject = "Активация предмета"
    email_content = f"""Добрый день!<br><br>

<b>{user.fullname}</b>{f' (<a href="https://t.me/{user.username}">@{user.username}</a>)' if user.username else ""} отправил запрос на активацию <b>{product.name}</b><br>
📝 Описание: {product.description}<br>
📍 Активаций: <b>{purchase.usage_count + 1}</b> из <b>{product.count}</b><br><br>

Для активации перейдите в <a href="https://t.me/{bot_username}">СТПшера</a>"""

    email = []

    match product.manager_role:
        case 3:
            if user.division == "НЦК":
                # Рассылка РГ НЦК
                email.append(config.mail.nck_email_addr)
            else:
                # Рассылка РГ НТП
                email.append(config.mail.ntp_email_addr)
        case 5:
            # Рассылка ГОК
            email.append(config.mail.gok_email_addr)
        case 6:
            # Рассылка МИП
            email.append(config.mail.mip_email_addr)

    # Почта руководителя сотрудника
    if user_head and user_head.email:
        email.append(user_head.email)

    # Почта текущего дежурного
    if current_duty and current_duty.email:
        email.append(current_duty.email)

    # Почта сотрудника, активировавшего предмет
    email.append(user.email)

    await send_email(addresses=email, subject=email_subject, body=email_content)
    logger.info(
        f"[Активация предмета] Уведомление об активации {product.name} пользователем {user.fullname} отправлено на {email}"
    )


async def send_cancel_product_email(
    user: Employee,
    user_head: Employee | None,
    current_duty: Employee | None,
    product: Product,
    purchase: Purchase,
    bot_username: str,
) -> None:
    """Отправляет письмо с уведомлением об отмене активации предмета.

    Args:
        user: Экземпляр пользователя с моделью Employee. Сотрудник, активировавший предмет
        user_head: Руководитель сотрудника, активировавшего предмет
        current_duty: Текущий дежурный
        product: Активируемый предмет
        purchase: Покупка, в рамках которой был приобретен предмет
        bot_username: Юзернейм бота Telegram
    """
    email_subject = "Отмена покупки"
    email_content = f"""Добрый день!<br><br>

<b>{user.fullname}</b>{f' (<a href="https://t.me/{user.username}">@{user.username}</a>)' if user.username else ""} отменил использование <b>{product.name}</b><br>
📝 Описание: {product.description}<br>
📍 Активаций: <b>{purchase.usage_count}</b> из <b>{product.count}</b><br><br>

Подробности можно посмотреть в <a href="https://t.me/{bot_username}">СТПшера</a>"""

    email = []
    match product.manager_role:
        case 3:
            if user.division == "НЦК":
                # Рассылка РГ НЦК
                email.append(config.mail.nck_email_addr)
            else:
                # Рассылка РГ НТП
                email.append(config.mail.ntp_email_addr)
        case 5:
            # Рассылка ГОК
            email.append(config.mail.gok_email_addr)
        case 6:
            # Рассылка МИП
            email.append(config.mail.mip_email_addr)

    # Почта руководителя сотрудника
    if user_head and user_head.email:
        email.append(user_head.email)

    # Почта текущего дежурного
    if current_duty and current_duty.email:
        email.append(current_duty.email)

    # Почта сотрудника, активировавшего предмет
    email.append(user.email)

    await send_email(addresses=email, subject=email_subject, body=email_content)
    logger.info(
        f"[Активация предмета] Уведомление об отмене активации {product.name} пользователем {user.fullname} отправлено на {email}"
    )
