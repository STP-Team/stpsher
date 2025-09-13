import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.handlers.group.whois import create_user_info_message, get_role_info
from tgbot.keyboards.user.main import MainMenu, auth_kb, main_kb

logger = logging.getLogger(__name__)

user_router = Router()
user_router.message.filter(F.chat.type == "private")
user_router.callback_query.filter(F.message.chat.type == "private")


@user_router.message(CommandStart())
async def user_start_cmd(message: Message, user: Employee):
    if not user:
        await message.answer(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    await message.answer(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>""",
        reply_markup=main_kb(),
    )


@user_router.callback_query(MainMenu.filter(F.menu == "main"))
async def user_start_cb(callback: CallbackQuery, user: Employee):
    if not user:
        await callback.message.edit_text(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    await callback.message.edit_text(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>""",
        reply_markup=main_kb(),
    )


@user_router.message(Command("whois"))
async def private_whois_command(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """Команда /whois для приватных сообщений - работает с пересланными сообщениями и аргументами"""
    
    # Проверяем авторизацию пользователя
    if not user:
        await message.reply(
            "❌ Для использования команды /whois необходимо авторизоваться в боте"
        )
        return
    
    # Проверяем, есть ли пересланное сообщение
    if message.forward_from:
        # Получаем информацию о пользователе из пересланного сообщения
        forwarded_user_id = message.forward_from.id
        
        try:
            # Ищем пользователя в базе данных
            target_user = await stp_repo.employee.get_user(user_id=forwarded_user_id)
            
            if not target_user:
                await message.reply(
                    f"""<b>❌ Пользователь не найден</b>

Пользователь с ID <code>{forwarded_user_id}</code> не найден в базе

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
                f"[WHOIS PRIVATE] {user.fullname} ({message.from_user.id}) запросил информацию о {target_user.fullname} ({target_user.user_id}) через пересланное сообщение"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды /whois в приватном чате: {e}")
            await message.reply(
                "❌ Произошла ошибка при получении информации о пользователе. Попробуйте позже."
            )
        return
    
    # Проверяем, есть ли аргументы для поиска
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) > 1:
        search_query = command_parts[1].strip()
        
        if len(search_query) < 1:
            await message.reply("❌ Поисковый запрос не может быть пустым")
            return
        
        try:
            target_user = None
            
            # Попытка поиска по user_id (если запрос состоит только из цифр)
            if search_query.isdigit():
                user_id = int(search_query)
                target_user = await stp_repo.employee.get_user(user_id=user_id)
                
                if target_user:
                    # Получаем информацию о руководителе
                    user_head = None
                    if target_user.head:
                        user_head = await stp_repo.employee.get_user(fullname=target_user.head)
                    
                    user_info_message = create_user_info_message(target_user, user_head)
                    await message.reply(user_info_message, parse_mode="HTML")
                    
                    logger.info(
                        f"[WHOIS PRIVATE] {user.fullname} ({message.from_user.id}) нашел по user_id '{search_query}': {target_user.fullname}"
                    )
                    return
            
            # Попытка поиска по username (если начинается с @ или похоже на username)
            username_query = search_query
            if username_query.startswith('@'):
                username_query = username_query[1:]  # Убираем @
            
            # Проверяем, похоже ли на username (без пробелов, может содержать буквы, цифры, подчеркивания)
            if username_query and all(c.isalnum() or c == '_' for c in username_query):
                target_user = await stp_repo.employee.get_user(username=username_query)
                
                if target_user:
                    # Получаем информацию о руководителе
                    user_head = None
                    if target_user.head:
                        user_head = await stp_repo.employee.get_user(fullname=target_user.head)
                    
                    user_info_message = create_user_info_message(target_user, user_head)
                    await message.reply(user_info_message, parse_mode="HTML")
                    
                    logger.info(
                        f"[WHOIS PRIVATE] {user.fullname} ({message.from_user.id}) нашел по username '{search_query}': {target_user.fullname}"
                    )
                    return
            
            # Если не найден по user_id или username, ищем по ФИО
            if len(search_query) < 2:
                await message.reply("❌ Поисковый запрос по имени слишком короткий (минимум 2 символа)")
                return
                
            # Поиск пользователей по частичному совпадению ФИО
            found_users = await stp_repo.employee.get_users_by_fio_parts(
                search_query, limit=10
            )
            
            if not found_users:
                await message.reply(
                    f"""<b>❌ Пользователь не найден</b>

По запросу "<code>{search_query}</code>" ничего не найдено.

<b>💡 Попробуй:</b>
• Поиск по ID: <code>/whois 123456789</code>
• Поиск по username: <code>/whois @roman_domru</code> или <code>/whois roman_domru</code>
• Поиск по имени: <code>/whois Иванов</code> или <code>/whois Петр Иванов</code>
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
                    f"[WHOIS PRIVATE] {user.fullname} ({message.from_user.id}) нашел по запросу '{search_query}': {target_user.fullname}"
                )
                return
            
            # Если найдено несколько пользователей, показываем список
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
• По ID: <code>/whois 123456789</code>
• По username: <code>/whois @username</code>
• По имени: <code>/whois Полное Имя</code>
• Inline-поиск: <code>@stpsher_bot {search_query}</code>
• Пересланное сообщение + <code>/whois</code>""",
                parse_mode="HTML",
            )
            
            # Логируем использование команды
            logger.info(
                f"[WHOIS PRIVATE] {user.fullname} ({message.from_user.id}) нашел {len(sorted_users)} пользователей по запросу '{search_query}'"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователей для команды /whois в приватном чате: {e}")
            await message.reply(
                "❌ Произошла ошибка при поиске пользователей. Попробуйте позже."
            )
        return
    
    # Если нет ни пересланного сообщения, ни аргументов - показываем инструкцию
    await message.reply(
        """<b>ℹ️ Использование команды /whois в приватном чате</b>

<b>Способы поиска:</b>

<b>1. По пересланному сообщению:</b>
• Перешлите мне сообщение от пользователя
• Отправьте команду <code>/whois</code>

<b>2. По Telegram ID:</b>
• <code>/whois 123456789</code>

<b>3. По username:</b>
• <code>/whois @roman_domru</code>
• <code>/whois roman_domru</code>

<b>4. По имени/фамилии:</b>
• <code>/whois Иванов</code>
• <code>/whois Петр</code>
• <code>/whois Иванов Петр</code>

<b>💡 Альтернатива:</b>
Используйте inline-поиск: <code>@stpsher_bot имя</code>""",
        parse_mode="HTML"
    )
