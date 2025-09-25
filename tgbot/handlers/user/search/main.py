import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.keyboards.user.main import MainMenu
from tgbot.keyboards.user.search.main import UserSearchMenu, user_search_main_kb
from tgbot.keyboards.user.search.search import (
    UserSearchUserResult,
    user_search_back_kb,
    user_search_results_kb,
    user_user_detail_kb,
)
from tgbot.misc.states.search import SearchEmployee
from tgbot.services.search import SearchService

user_search_router = Router()

# Фильтры для роутера - обрабатываем запросы от обычных пользователей (роли 1 и 3)
user_search_router.message.filter(F.chat.type == "private")
user_search_router.callback_query.filter(F.message.chat.type == "private")

logger = logging.getLogger(__name__)

# Константы для пагинации
USERS_PER_PAGE = 10


@user_search_router.callback_query(MainMenu.filter(F.menu == "search"))
async def user_search_main_menu(
    callback: CallbackQuery, state: FSMContext, user: Employee
):
    """Главное меню поиска для обычных пользователей"""
    await state.clear()

    # Проверяем права доступа - только роли 1 и 3
    if user.role not in [1, 3]:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    await callback.message.edit_text(
        """<b>🕵🏻 Поиск сотрудника</b>

<i>Выбери должность искомого человека или воспользуйся общим поиском</i>""",
        reply_markup=user_search_main_kb(),
    )


@user_search_router.callback_query(UserSearchMenu.filter())
async def user_search_menu_handler(
    callback: CallbackQuery,
    callback_data: UserSearchMenu,
    stp_repo: MainRequestsRepo,
    state: FSMContext,
    user: Employee,
):
    """Обработка меню поиска для обычных пользователей"""
    # Проверяем права доступа
    if user.role not in [1, 3]:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    menu = callback_data.menu

    if menu == "specialists":
        await show_user_specialists(callback, callback_data, stp_repo)
    elif menu == "heads":
        await show_user_heads(callback, callback_data, stp_repo)
    elif menu == "start_search":
        await start_user_search(callback, state)


async def show_user_specialists(
    callback: CallbackQuery,
    callback_data: UserSearchMenu,
    stp_repo: MainRequestsRepo,
):
    """Показать всех специалистов для обычных пользователей"""
    page = callback_data.page

    # Получаем всех пользователей и фильтруем специалистов
    all_users = await stp_repo.employee.get_users()
    if not all_users:
        await callback.answer("❌ Пользователи не найдены", show_alert=True)
        return

    specialists = SearchService.filter_users_by_type(all_users, "specialists")

    if not specialists:
        await callback.answer("❌ Специалисты не найдены", show_alert=True)
        return

    # Сортировка по алфавиту
    specialists.sort(key=lambda u: u.fullname)

    # Пагинация
    total_users = len(specialists)
    total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE

    start_idx = (page - 1) * USERS_PER_PAGE
    end_idx = start_idx + USERS_PER_PAGE
    page_users = specialists[start_idx:end_idx]

    await callback.message.edit_text(
        f"""<b>👤 Специалисты</b>

Найдено специалистов: {total_users}
Страница {page} из {total_pages}""",
        reply_markup=user_search_results_kb(
            page_users,
            page,
            total_pages,
            "specialists",
        ),
    )


async def show_user_heads(
    callback: CallbackQuery,
    callback_data: UserSearchMenu,
    stp_repo: MainRequestsRepo,
):
    """Показать всех руководителей для обычных пользователей"""
    page = callback_data.page

    # Получаем всех пользователей и фильтруем руководителей
    all_users = await stp_repo.employee.get_users()
    if not all_users:
        await callback.answer("❌ Пользователи не найдены", show_alert=True)
        return

    heads = SearchService.filter_users_by_type(all_users, "heads")

    if not heads:
        await callback.answer("❌ Руководители не найдены", show_alert=True)
        return

    # Сортировка по алфавиту
    heads.sort(key=lambda u: u.fullname)

    # Пагинация
    total_users = len(heads)
    total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE

    start_idx = (page - 1) * USERS_PER_PAGE
    end_idx = start_idx + USERS_PER_PAGE
    page_users = heads[start_idx:end_idx]

    await callback.message.edit_text(
        f"""<b>👑 Руководители</b>

Найдено руководителей: {total_users}
Страница {page} из {total_pages}""",
        reply_markup=user_search_results_kb(
            page_users,
            page,
            total_pages,
            "heads",
        ),
    )


async def start_user_search(callback: CallbackQuery, state: FSMContext):
    """Начать поиск по имени для обычных пользователей"""
    bot_message = await callback.message.edit_text(
        """<b>🕵🏻 Поиск сотрудника</b>

Введи часть имени, фамилии или полное ФИО сотрудника:

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
        reply_markup=user_search_back_kb(),
    )

    await state.update_data(bot_message_id=bot_message.message_id)
    await state.set_state(SearchEmployee.waiting_search_query)


@user_search_router.message(SearchEmployee.waiting_search_query)
async def process_user_search_query(
    message: Message, state: FSMContext, stp_repo: MainRequestsRepo
):
    """Обработка поискового запроса для обычных пользователей"""
    search_query = message.text.strip()
    state_data = await state.get_data()
    bot_message_id = state_data.get("bot_message_id")

    # Удаляем сообщение пользователя
    await message.delete()

    if not search_query or len(search_query) < 2:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text="""<b>🕵🏻 Поиск сотрудника</b>

❌ Поисковый запрос слишком короткий (минимум 2 символа)

Введи часть имени, фамилии или полное ФИО сотрудника:

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
            reply_markup=user_search_back_kb(),
        )
        return

    try:
        # Поиск пользователей по частичному совпадению ФИО
        found_users = await stp_repo.employee.get_users_by_fio_parts(
            search_query, limit=50
        )

        if not found_users:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=bot_message_id,
                text=f"""<b>🕵🏻 Поиск сотрудника</b>

❌ По запросу "<code>{search_query}</code>" ничего не найдено

Попробуй другой запрос или проверь правильность написания

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
                reply_markup=user_search_back_kb(),
            )
            return

        # Сортировка результатов
        sorted_users = sorted(
            found_users,
            key=lambda u: (
                search_query.lower() not in u.fullname.lower(),
                u.fullname,
            ),
        )

        # Пагинация результатов
        total_found = len(sorted_users)
        total_pages = (total_found + USERS_PER_PAGE - 1) // USERS_PER_PAGE
        page_users = sorted_users[:USERS_PER_PAGE]

        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text=f"""<b>🔍 Результаты поиска</b>

По запросу "<code>{search_query}</code>" найдено: {total_found} сотрудников""",
            reply_markup=user_search_results_kb(
                page_users,
                1,
                total_pages,
                "search_results",
            ),
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при поиске пользователей: {e}")
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text="""<b>🕵🏻 Поиск сотрудника</b>

❌ Произошла ошибка при поиске. Попробуй позже

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
            reply_markup=user_search_back_kb(),
        )


@user_search_router.callback_query(UserSearchUserResult.filter())
async def show_user_search_details(
    callback: CallbackQuery,
    callback_data: UserSearchUserResult,
    stp_repo: MainRequestsRepo,
    user: Employee,
):
    """Показать информацию о найденном пользователе для обычных пользователей"""
    # Проверяем права доступа
    if user.role not in [1, 3]:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    user_id = callback_data.user_id
    return_to = callback_data.return_to

    try:
        target_user = await stp_repo.employee.get_user(user_id=user_id)
        user_head = (
            await stp_repo.employee.get_user(fullname=target_user.head)
            if target_user.head
            else None
        )

        if not target_user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Базовая информация о пользователе (без статистики для обычных пользователей)
        user_info = SearchService.format_user_info_role_based(
            target_user, user_head, None, user.role
        )

        await callback.message.edit_text(
            user_info,
            reply_markup=user_user_detail_kb(target_user, return_to),
        )

    except Exception as e:
        logger.error(f"Ошибка при получении информации о пользователе: {e}")
        await callback.answer("❌ Ошибка при получении данных", show_alert=True)
