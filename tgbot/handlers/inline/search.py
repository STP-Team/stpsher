import logging
from typing import List

from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from stp_database.models.STP import Employee
from stp_database.repo.STP import MainRequestsRepo

from tgbot.handlers.inline.helpers import SEARCH_LIMITS
from tgbot.handlers.inline.texts import ERROR_MESSAGES
from tgbot.misc.helpers import format_fullname, get_role

logger = logging.getLogger(__name__)


async def handle_search_query(
    query_text: str, stp_repo: MainRequestsRepo
) -> List[InlineQueryResultArticle]:
    """Обработка inline запросов поиска пользователей.

    Args:
        query_text: Текст поискового запроса
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Список найденных пользователей
    """
    if not query_text or len(query_text) < 2:
        return []

    try:
        # Используем тот же простой поиск, что и в диалогах
        found_users = await stp_repo.employee.search_users(query_text, limit=50)

        if not found_users:
            # Результаты не найдены
            return [InlineResultBuilder.create_no_results(query_text)]

        # Применяем ту же логику сортировки, что и в диалогах
        sorted_users = _sort_search_results(found_users, query_text)

        # Ограничиваем результаты для inline отображения
        limited_users = sorted_users[: SEARCH_LIMITS["MAX_DISPLAY_RESULTS"]]

        results = []
        for found_user in limited_users:
            user_head = await _get_user_head(stp_repo, found_user.head)
            result_item = InlineResultBuilder.create_user_result(
                found_user, user_head, query_text
            )
            results.append(result_item)

        return results

    except Exception as e:
        logger.error(f"[Inline] Ошибка при поиске пользователей: {e}")
        return [InlineResultBuilder.create_error_result(e)]


async def _get_user_head(stp_repo: MainRequestsRepo, head_name: str) -> Employee:
    """Получение информации о руководителе пользователя.

    Args:
        stp_repo: Репозиторий операций с базой STP
        head_name: Полное имя руководителя

    Returns:
        Объект Employee руководителя или None, если не найден
    """
    if not head_name:
        return None

    try:
        return await stp_repo.employee.get_users(fullname=head_name)
    except Exception as e:
        logger.warning(f"[Inline] Не удалось найти руководителя '{head_name}': {e}")
        return None


def _sort_search_results(users: List[Employee], query_text: str) -> List[Employee]:
    """Сортировка результатов поиска по релевантности.

    Args:
        users: Список пользователей для сортировки
        query_text: Поисковый запрос для определения релевантности

    Returns:
        Отсортированный список пользователей
    """
    return sorted(
        users,
        key=lambda u: (
            # Сначала полные совпадения
            query_text.lower() not in u.fullname.lower(),
            # Потом по алфавиту
            u.fullname,
        ),
    )


class InlineResultBuilder:
    """Класс для создания различных типов inline query результатов."""

    @staticmethod
    def create_user_result(
        user: Employee, user_head: Employee, search_query: str
    ) -> InlineQueryResultArticle:
        """Создание элемента результата для найденного пользователя.

        Args:
            user: Найденный пользователь
            user_head: Руководитель пользователя (может быть None)
            search_query: Поисковый запрос

        Returns:
            Элемент результата для inline query
        """
        # Определяем роль и эмодзи
        role_info = get_role(user.role)

        # Подготавливаем описание
        description_parts = []
        if user.division:
            description_parts.append(user.division)
        if user.position:
            description_parts.append(user.position)

        description = (
            " • ".join(description_parts) if description_parts else role_info["name"]
        )

        # Формируем контент сообщения
        message_parts = [f"<b>{role_info['emoji']} {user.fullname}</b>", ""]

        if user.position and user.division:
            message_parts.append(
                f"<b>💼 Должность:</b> {user.position} {user.division}"
            )
        if user.head:
            if user_head:
                message_parts.append(
                    f"<b>👑 Руководитель:</b> {format_fullname(user_head, True, True)}"
                )
            else:
                message_parts.append(f"<b>👑 Руководитель:</b> {user.head}")

        message_parts.append("")

        # Контактная информация
        if user.username:
            message_parts.append(f"<b>📱 Telegram:</b> @{user.username}")
        if user.email:
            message_parts.append(f"<b>📧 Email:</b> {user.email}")

        message_parts.append(
            f"\n🛡️ <b>Уровень доступа:</b> {get_role(user.role)['name']}"
        )

        message_text = "\n".join(message_parts)

        return InlineQueryResultArticle(
            id=f"user_{user.id}",
            title=f"{role_info['emoji']} {user.fullname}",
            description=description,
            input_message_content=InputTextMessageContent(
                message_text=message_text, parse_mode="HTML"
            ),
        )

    @staticmethod
    def create_no_results(query_text: str) -> InlineQueryResultArticle:
        """Создание элемента для случая, когда ничего не найдено.

        Args:
            query_text: Поисковый запрос, который не дал результатов

        Returns:
            Элемент результата с сообщением об отсутствии результатов
        """
        message_parts = [
            ERROR_MESSAGES["NO_RESULTS"],
            "",
            f"<b>Поисковый запрос:</b> <code>{query_text}</code>",
            "",
            "<b>💡 Попробуйте:</b>",
            "• Проверить правильность написания",
            "• Использовать только часть имени или фамилии",
            "• Попробовать поиск по ID или username",
            "",
            "<b>📝 Примеры поиска:</b>",
            "• <code>Иванов</code> - поиск по фамилии",
            "• <code>123456789</code> - поиск по ID пользователя",
            "• <code>@username</code> - поиск по username",
        ]

        return InlineQueryResultArticle(
            id="no_users_found",
            title=ERROR_MESSAGES["NO_RESULTS"],
            description=f"По запросу: {query_text}",
            input_message_content=InputTextMessageContent(
                message_text="\n".join(message_parts), parse_mode="HTML"
            ),
        )

    @staticmethod
    def create_error_result(error: Exception) -> InlineQueryResultArticle:
        """Создание элемента для ошибки.

        Args:
            error: Исключение, которое произошло во время поиска

        Returns:
            Элемент результата с сообщением об ошибке
        """
        return InlineQueryResultArticle(
            id="search_error",
            title=ERROR_MESSAGES["SEARCH_ERROR"],
            description="Произошла ошибка при поиске пользователей",
            input_message_content=InputTextMessageContent(
                message_text=f"{ERROR_MESSAGES['GENERAL_ERROR']}\n\nПопробуйте еще раз или обратитесь к администратору для проверки данных\n\n<i>Код ошибки: {type(error).__name__}</i>"
            ),
        )
