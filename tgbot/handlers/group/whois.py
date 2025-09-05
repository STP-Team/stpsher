import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo

logger = logging.getLogger(__name__)

whois_router = Router()
whois_router.message.filter(F.chat.type == "group")


def get_role_info(role: int) -> dict:
    """Получение информации о роли пользователя"""
    roles = {
        1: {
            "emoji": "👤",
            "text": "Сотрудник",
        },
        2: {
            "emoji": "👑",
            "text": "Руководитель",
        },
        3: {
            "emoji": "👮‍♂️",
            "text": "Дежурный",
        },
        10: {
            "emoji": "⚡",
            "text": "Администратор",
        },
    }
    return roles.get(role, roles[1])


def create_user_info_message(user: Employee, user_head: Employee = None) -> str:
    """Создание сообщения с информацией о пользователе (аналогично inline search)"""

    # Определяем уровень доступа и эмодзи
    role_info = get_role_info(user.role)

    # Формируем контент сообщения
    message_parts = [f"<b>{role_info['emoji']} {user.fullname}</b>", ""]

    if user.position and user.division:
        message_parts.append(f"<b>💼 Должность:</b> {user.position} {user.division}")
    if user.head:
        if user_head and user_head.username:
            message_parts.append(
                f"<b>👑 Руководитель:</b> <a href='t.me/{user_head.username}'>{user.head}</a>"
            )
        else:
            message_parts.append(f"<b>👑 Руководитель:</b> {user.head}")

    message_parts.append("")

    # Контактная информация
    if user.username:
        message_parts.append(f"<b>📱 Telegram:</b> @{user.username}")
    if user.email:
        message_parts.append(f"<b>📧 Email:</b> {user.email}")

    message_parts.append(f"\n🛡️ <b> Уровень доступа:</b> {role_info['text']}")

    return "\n".join(message_parts)


@whois_router.message(Command("whois"))
async def whois_command(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """Команда /whois для получения информации о пользователе"""

    # Проверяем авторизацию пользователя
    if not user:
        await message.reply(
            "❌ Для использования команды /whois необходимо авторизоваться в боте"
        )
        return

    # Проверяем, является ли сообщение ответом на другое сообщение
    if not message.reply_to_message:
        await message.reply(
            """<b>ℹ️ Использование команды /whois</b>

<b>Как использовать:</b>
Ответь командой <code>/whois</code> на сообщение пользователя, информацию о котором хочешь получить

<b>Пример:</b>
1. Найди сообщение от нужного пользователя
2. Ответь на него командой <code>/whois</code>
3. Получи подробную информацию о пользователе

<b>💡 Альтернатива:</b>
Используй inline-поиск: <code>@stpsher_bot Иванов</code>"""
        )
        return

    # Получаем информацию о пользователе из replied сообщения
    replied_user_id = message.reply_to_message.from_user.id

    try:
        # Ищем пользователя в базе данных
        target_user = await stp_repo.employee.get_user(user_id=replied_user_id)

        if not target_user:
            await message.reply(
                f"""<b>❌ Пользователь не найден</b>

Пользователь с ID <code>{replied_user_id}</code> не найден в базе

<b>Возможные причины:</b>
• Пользователь не авторизован в боте
• Пользователь не является сотрудником СТП
• Пользователь был удален из базы данных

<b>💡 Подсказка:</b>
Для получения данных искомому пользователю необходимо авторизоваться в @stpsher_bot"""
            )
            return

        # Получаем информацию о руководителе, если указан
        user_head = None
        if target_user.head:
            user_head = await stp_repo.employee.get_user(fullname=target_user.head)

        # Формируем и отправляем ответ с информацией о пользователе
        user_info_message = create_user_info_message(target_user, user_head)

        await message.reply(user_info_message, parse_mode="HTML")

        # Логируем использование команды
        logger.info(
            f"[WHOIS] {user.fullname} ({message.from_user.id}) запросил информацию о {target_user.fullname} ({target_user.user_id})"
        )

    except Exception as e:
        logger.error(f"Ошибка при выполнении команды /whois: {e}")
        await message.reply(
            "❌ Произошла ошибка при получении информации о пользователе. Попробуйте позже."
        )


# Дополнительный хэндлер для команды /whois с аргументом (поиск по имени)
@whois_router.message(Command("whois", magic=F.args))
async def whois_with_args(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """Команда /whois с аргументом для поиска по имени"""

    # Проверяем авторизацию пользователя
    if not user:
        await message.reply(
            "❌ Для использования команды /whois необходимо авторизоваться в боте"
        )
        return

    search_query = message.text.split(maxsplit=1)[1].strip()

    if len(search_query) < 2:
        await message.reply("❌ Поисковый запрос слишком короткий (минимум 2 символа)")
        return

    try:
        # Поиск пользователей по частичному совпадению ФИО
        found_users = await stp_repo.employee.get_users_by_fio_parts(
            search_query, limit=10
        )

        if not found_users:
            await message.reply(
                f"""<b>❌ Пользователи не найдены</b>

По запросу "<code>{search_query}</code>" ничего не найдено.

<b>💡 Попробуй:</b>
• Проверить правильность написания
• Использовать только часть имени или фамилии
• Использовать inline-поиск: <code>@stpsher_bot {search_query}</code>"""
            )
            return

        # Если найден только один пользователь, показываем полную информацию
        if len(found_users) == 1:
            target_user = found_users[0]

            # Получаем информацию о руководителе
            user_head = None
            if target_user.head:
                user_head = await stp_repo.employee.get_user(fullname=target_user.head)

            user_info_message = create_user_info_message(target_user, user_head)
            await message.reply(user_info_message, parse_mode="HTML")

            # Логируем использование команды
            logger.info(
                f"[WHOIS] {user.fullname} ({message.from_user.id}) нашел по запросу '{search_query}': {target_user.fullname}"
            )
            return

        # Если найдено несколько пользователей, показываем список
        # Сортируем результаты (сначала точные совпадения)
        sorted_users = sorted(
            found_users,
            key=lambda u: (
                search_query.lower() not in u.fullname.lower(),
                u.fullname,
            ),
        )

        # Формируем список найденных пользователей
        user_list = []
        for idx, found_user in enumerate(sorted_users, 1):
            role_info = get_role_info(found_user.role)
            user_entry = f"{idx}. <b>{role_info['emoji']} {found_user.fullname}</b>"

            if found_user.position and found_user.division:
                user_entry += f"\n   💼 {found_user.position} {found_user.division}"

            if found_user.username:
                user_entry += f"\n   📱 @{found_user.username}"

            user_list.append(user_entry)

        users_text = "\n\n".join(user_list)

        await message.reply(
            f"""<b>🔍 Найдено пользователей: {len(sorted_users)}</b>

По запросу "<code>{search_query}</code>":

{users_text}

<b>💡 Для получения подробной информации:</b>
• Ответьте командой <code>/whois</code> на сообщение нужного пользователя
• Используйте inline-поиск: <code>@stpsher_bot {search_query}</code>""",
            parse_mode="HTML",
        )

        # Логируем использование команды
        logger.info(
            f"[WHOIS] {user.fullname} ({message.from_user.id}) нашел {len(sorted_users)} пользователей по запросу '{search_query}'"
        )

    except Exception as e:
        logger.error(f"Ошибка при поиске пользователей для команды /whois: {e}")
        await message.reply(
            "❌ Произошла ошибка при поиске пользователей. Попробуйте позже."
        )


# Если создаете новый файл, экспортируйте роутер
__all__ = ["whois_router"]
