import logging
from typing import List

from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import (
    AdministratorFilter,
    MipFilter,
    MultiRoleFilter,
    RootFilter,
    SpecialistFilter, DutyFilter,
)
from tgbot.handlers.user.schedule.main import schedule_service

logger = logging.getLogger(__name__)

user_inline_router = Router()
user_inline_router.inline_query.filter(
    MultiRoleFilter(
        SpecialistFilter(), AdministratorFilter(), MipFilter(), RootFilter(), DutyFilter()
    )
)


class InlineSearchFilter:
    """Класс для обработки фильтров поиска в inline запросах"""

    @staticmethod
    def parse_search_query(query: str) -> dict:
        """
        Парсинг поискового запроса с поддержкой фильтров

        Примеры запросов:
        - "Иванов" - обычный поиск
        - "div:НТП Иванов" - поиск по направлению
        - "role:head Петров" - поиск руководителей
        - "pos:инженер" - поиск по должности
        """
        filters = {"name": "", "division": None, "role": None, "position": None}

        parts = query.strip().split()
        name_parts = []

        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                if key == "div" and value:
                    filters["division"] = value
                elif key == "role" and value:
                    if value in ["head", "руководитель"]:
                        filters["role"] = 2
                    elif value in ["admin", "администратор"]:
                        filters["role"] = 3
                    elif value in ["user", "пользователь", "сотрудник"]:
                        filters["role"] = 1
                elif key == "pos" and value:
                    filters["position"] = value
            else:
                name_parts.append(part)

        filters["name"] = " ".join(name_parts)
        return filters

    @staticmethod
    async def search_users_with_filters(
        stp_repo, filters: dict, limit: int = 20
    ) -> List[Employee]:
        """Поиск пользователей с применением фильтров"""
        try:
            # Базовый поиск по имени
            if filters["name"]:
                users = await stp_repo.employee.get_users_by_fio_parts(
                    filters["name"], limit=50
                )
            else:
                users = await stp_repo.employee.get_users()
                users = list(users) if users else []

            if not users:
                return []

            # Применяем дополнительные фильтры
            filtered_users = []
            for user in users:
                # Фильтр по направлению
                if filters["division"] and user.division:
                    if filters["division"].lower() not in user.division.lower():
                        continue

                # Фильтр по роли
                if filters["role"] is not None:
                    if user.role != filters["role"]:
                        continue

                # Фильтр по должности
                if filters["position"] and user.position:
                    if filters["position"].lower() not in user.position.lower():
                        continue

                filtered_users.append(user)

                # Ограничиваем количество результатов
                if len(filtered_users) >= limit:
                    break

            return filtered_users

        except Exception as e:
            logger.error(f"Error in filtered user search: {e}")
            return []


@user_inline_router.inline_query()
async def advanced_inline_handler(
    inline_query: InlineQuery, user: Employee, stp_repo: MainRequestsRepo
):
    """Продвинутый обработчик инлайн-запросов с поиском и фильтрами"""
    query_text = inline_query.query.strip()

    if not user:
        results = [
            InlineQueryResultArticle(
                id="auth_help",
                title="❌ Требуется авторизация",
                description="Авторизуйтесь в боте для использования функций",
                input_message_content=InputTextMessageContent(
                    message_text="❌ Для использования функций бота необходимо авторизоваться @stpsher_bot"
                ),
            )
        ]
    else:
        results = []

        # Обработка поискового запроса
        if query_text and len(query_text) >= 2:
            search_filters = InlineSearchFilter.parse_search_query(query_text)

            try:
                # Поиск пользователей с фильтрами
                found_users = await InlineSearchFilter.search_users_with_filters(
                    stp_repo, search_filters, limit=15
                )

                if found_users:
                    # Сортировка результатов
                    sorted_users = sorted(
                        found_users,
                        key=lambda u: (
                            # Приоритет для точных совпадений по имени
                            search_filters["name"].lower() not in u.fullname.lower()
                            if search_filters["name"]
                            else False,
                            # Приоритет для руководителей
                            u.role != 2,
                            # По алфавиту
                            u.fullname,
                        ),
                    )

                    # Добавляем результаты поиска
                    for found_user in sorted_users[:12]:  # Максимум 12 результатов
                        user_head = await stp_repo.employee.get_user(
                            fullname=found_user.head
                        )
                        result_item = create_user_result_item(
                            found_user, user_head, search_filters
                        )
                        results.append(result_item)

                # Если ничего не найдено
                if not found_users:
                    results.append(create_no_results_item(query_text, search_filters))

                # Добавляем подсказки по фильтрам
                if len(results) < 5:  # Добавляем подсказки только если мало результатов
                    results.extend(create_filter_hints(query_text))

            except Exception as e:
                logger.error(f"Error in advanced search: {e}")
                results.append(create_error_item(e))

        # Дефолтные команды, если нет поискового запроса
        else:
            results.extend(await create_default_commands(user, stp_repo))

    # Динамическое время кеширования
    cache_time = get_cache_time(query_text, results)

    await inline_query.answer(results, cache_time=cache_time, is_personal=True)


def create_user_result_item(
    user: Employee, user_head: Employee, search_filters: dict
) -> InlineQueryResultArticle:
    """Создание элемента результата для найденного пользователя"""
    # Определяем роль и эмодзи
    role_info = get_role_info(user.role)

    # Подготавливаем описание
    description_parts = []
    if user.division:
        description_parts.append(user.division)
    if user.position:
        description_parts.append(user.position)

    description = (
        " • ".join(description_parts) if description_parts else role_info["text"]
    )

    # Формируем контент сообщения
    message_parts = [f"<b>{role_info['emoji']} {user.fullname}</b>", ""]

    if user.position and user.division:
        message_parts.append(f"<b>💼 Должность:</b> {user.position} {user.division}")
    if user.head:
        if user_head:
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

    message_parts.append(f"\n🛡️ <b>Уровень доступа:</b> {role_info['text']}")

    # Добавляем информацию о том, по какому фильтру найден пользователь
    match_info = []
    if (
        search_filters["division"]
        and user.division
        and search_filters["division"].lower() in user.division.lower()
    ):
        match_info.append(f"направление: {user.division}")
    if (
        search_filters["position"]
        and user.position
        and search_filters["position"].lower() in user.position.lower()
    ):
        match_info.append(f"должность: {user.position}")
    if search_filters["role"] is not None and user.role == search_filters["role"]:
        match_info.append(f"роль: {role_info['text'].lower()}")

    if match_info:
        message_parts.append("")
        message_parts.append(f"<i>🎯 Найден по: {', '.join(match_info)}</i>")

    message_text = "\n".join(message_parts)

    return InlineQueryResultArticle(
        id=f"user_{user.id}",
        title=f"{role_info['emoji']} {user.fullname}",
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=message_text, parse_mode="HTML"
        ),
    )


def create_no_results_item(
    query_text: str, search_filters: dict
) -> InlineQueryResultArticle:
    """Создание элемента для случая, когда ничего не найдено"""
    # Анализируем фильтры для более детального сообщения
    filter_info = []
    if search_filters["name"]:
        filter_info.append(f"имя: '{search_filters['name']}'")
    if search_filters["division"]:
        filter_info.append(f"направление: '{search_filters['division']}'")
    if search_filters["position"]:
        filter_info.append(f"должность: '{search_filters['position']}'")
    if search_filters["role"] is not None:
        role_names = {1: "сотрудник", 2: "руководитель", 3: "администратор"}
        filter_info.append(
            f"роль: '{role_names.get(search_filters['role'], 'неизвестно')}'"
        )

    filter_text = ", ".join(filter_info) if filter_info else query_text

    message_parts = [
        "❌ <b>Пользователи не найдены</b>",
        "",
        f"<b>Поисковый запрос:</b> <code>{query_text}</code>",
        f"<b>Критерии поиска:</b> {filter_text}",
        "",
        "<b>💡 Попробуйте:</b>",
        "• Проверить правильность написания",
        "• Использовать только часть имени или фамилии",
        "• Убрать фильтры и искать только по имени",
        "",
        "<b>📝 Примеры поиска:</b>",
        "• <code>Иванов</code> - поиск по фамилии",
        "• <code>div:НТП Петров</code> - поиск в направлении",
        "• <code>role:head</code> - поиск руководителей",
    ]

    return InlineQueryResultArticle(
        id="no_users_found",
        title="❌ Пользователи не найдены",
        description=f"По критериям: {filter_text}",
        input_message_content=InputTextMessageContent(
            message_text="\n".join(message_parts), parse_mode="HTML"
        ),
    )


def create_filter_hints(query_text: str) -> List[InlineQueryResultArticle]:
    """Создание подсказок по фильтрам поиска"""
    hints = [
        InlineQueryResultArticle(
            id="hint_heads",
            title="💡 Найти руководителей",
            description="Добавь role:head к запросу",
            input_message_content=InputTextMessageContent(
                message_text=f"<b>💡 Подсказка по поиску</b>\n\nДобавь <code>role:head</code> к запросу для поиска только руководителей:\n\n<code>{query_text} role:head</code>"
            ),
        ),
        InlineQueryResultArticle(
            id="hint_division",
            title="💡 Поиск по направлению",
            description="Используй div:НТП или div:НЦК",
            input_message_content=InputTextMessageContent(
                message_text=f"<b>💡 Подсказка по поиску</b>\n\nДля поиска в определенном направлении используй:\n\n<code>{query_text} div:НТП</code>\n<code>{query_text} div:НЦК</code>"
            ),
        ),
    ]

    return hints


def create_error_item(error: Exception) -> InlineQueryResultArticle:
    """Создание элемента для ошибки"""
    return InlineQueryResultArticle(
        id="search_error",
        title="❌ Ошибка поиска",
        description="Произошла ошибка при поиске пользователей",
        input_message_content=InputTextMessageContent(
            message_text=f"❌ <b>Ошибка при поиске пользователей</b>\n\nПопробуйте еще раз или обратитесь к администратору.\n\n<i>Код ошибки: {type(error).__name__}</i>"
        ),
    )


async def create_default_commands(
    user: Employee, stp_repo
) -> List[InlineQueryResultArticle]:
    """Создание дефолтных команд"""
    results = []

    # Мой график
    try:
        current_month = schedule_service.get_current_month()
        schedule_text = await schedule_service.get_user_schedule_response(
            user=user, month=current_month, compact=True
        )
        if schedule_text:
            results.append(
                InlineQueryResultArticle(
                    id="schedule_option",
                    title="📅 Мой график",
                    description=f"Твой график на {current_month}",
                    input_message_content=InputTextMessageContent(
                        message_text=schedule_text, parse_mode="HTML"
                    ),
                )
            )
    except Exception as e:
        logger.error(f"Error getting schedule: {e}")

    # Дежурные на сегодня
    try:
        duties_text = await schedule_service.get_duties_response(
            division=user.division, stp_repo=stp_repo
        )
        if duties_text:
            results.append(
                InlineQueryResultArticle(
                    id="duties_option",
                    title="👮‍♂️ Дежурные на сегодня",
                    description=f"График дежурных {user.division}",
                    input_message_content=InputTextMessageContent(
                        message_text=duties_text, parse_mode="HTML"
                    ),
                )
            )
    except Exception as e:
        logger.error(f"Error getting duties: {e}")

    # Руководители на сегодня
    try:
        heads_text = await schedule_service.get_heads_response(
            division=user.division, stp_repo=stp_repo
        )
        if heads_text:
            results.append(
                InlineQueryResultArticle(
                    id="heads_option",
                    title="👑 Руководители на сегодня",
                    description=f"График руководителей {user.division}",
                    input_message_content=InputTextMessageContent(
                        message_text=heads_text, parse_mode="HTML"
                    ),
                )
            )
    except Exception as e:
        logger.error(f"Error getting heads: {e}")

    return results


def create_search_help_item() -> InlineQueryResultArticle:
    """Создание справки по поиску"""
    help_text = """<b>🔍 Поиск сотрудников</b>

<b>Основные команды:</b>
• Просто введите имя или фамилию для поиска
• Можно искать по части имени

<b>Продвинутые фильтры:</b>
• <code>role:head</code> - только руководители
• <code>role:admin</code> - только администраторы  
• <code>role:user</code> - только сотрудники
• <code>div:НТП</code> - поиск в направлении НТП
• <code>div:НЦК</code> - поиск в направлении НЦК
• <code>pos:инженер</code> - поиск по должности

<b>Примеры запросов:</b>
• <code>Иванов</code>
• <code>Петр role:head</code>
• <code>div:НТП Сидоров</code>
• <code>pos:инженер div:НЦК</code>

<b>💡 Совет:</b> Комбинируйте фильтры для точного поиска!</b>"""

    return InlineQueryResultArticle(
        id="search_help",
        title="🔍 Поиск сотрудников",
        description="Введите имя или используйте фильтры для поиска",
        input_message_content=InputTextMessageContent(
            message_text=help_text, parse_mode="HTML"
        ),
    )


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


def get_cache_time(query_text: str, results: list) -> int:
    """Определение времени кеширования в зависимости от запроса"""
    if not query_text:
        # Дефолтные команды кешируем на минуту
        return 60
    elif len(results) == 0 or any(result.id.endswith("_error") for result in results):
        # Ошибки или пустые результаты не кешируем
        return 0
    else:
        # Результаты поиска кешируем на 5 минут
        return 300
