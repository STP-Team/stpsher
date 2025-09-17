# tgbot/handlers/mip/search.py
import logging
from typing import Sequence

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.handlers.user.schedule.main import schedule_service
from tgbot.keyboards.mip.search import (
    EditUserMenu,
    HeadGroupMembersMenuForSearch,
    HeadGroupMenu,
    HeadMemberActionMenuForSearch,
    HeadMemberDetailMenuForSearch,
    HeadMemberRoleChangeForSearch,
    MipScheduleNavigation,
    SearchMenu,
    SearchUserResult,
    SelectUserRole,
    ViewUserSchedule,
    edit_user_back_kb,
    get_month_name_by_index,
    head_group_members_kb_for_search,
    head_member_detail_kb_for_search,
    role_selection_kb,
    search_back_kb,
    search_main_kb,
    search_results_kb,
    user_detail_kb,
    user_schedule_with_month_kb,
)
from tgbot.keyboards.user.main import MainMenu
from tgbot.misc.dicts import role_names
from tgbot.misc.states.mip.search import EditEmployee, SearchEmployee
from tgbot.services.leveling import LevelingSystem

mip_search_router = Router()
mip_search_router.message.filter(F.chat.type == "private", MipFilter())
mip_search_router.callback_query.filter(F.message.chat.type == "private", MipFilter())

logger = logging.getLogger(__name__)

# Константы для пагинации
USERS_PER_PAGE = 10


def filter_users_by_type(users: Sequence[Employee], search_type: str) -> list[Employee]:
    """
    Фильтрация пользователей по типу поиска

    :param users: Список пользователей
    :param search_type: Тип поиска (specialists, heads, all)
    :return: Отфильтрованный список пользователей
    """
    if search_type == "specialists":
        # Специалисты - роль 1 (обычные пользователи)
        return [user for user in users if user.role == 1]
    elif search_type == "heads":
        # Руководители - роль 2 (головы)
        return [user for user in users if user.role == 2]
    else:
        # Все пользователи
        return list(users)


async def get_user_statistics(user_id: int, stp_repo: MainRequestsRepo) -> dict:
    """Получить статистику пользователя (уровень, очки, достижения, покупки)"""
    try:
        # Получаем базовые данные
        user_purchases = await stp_repo.purchase.get_user_purchases(user_id)
        achievements_sum = await stp_repo.transaction.get_user_achievements_sum(user_id)
        purchases_sum = await stp_repo.purchase.get_user_purchases_sum(user_id)

        # Рассчитываем уровень
        user_balance = await stp_repo.transaction.get_user_balance(user_id)
        current_level = LevelingSystem.calculate_level(achievements_sum)

        return {
            "level": current_level,
            "balance": user_balance,
            "total_earned": achievements_sum,
            "total_spent": purchases_sum,
            "purchases_count": len(user_purchases),
        }
    except Exception as e:
        logger.error(f"Ошибка получения статистики пользователя {user_id}: {e}")
        return {
            "level": 0,
            "balance": 0,
            "total_earned": 0,
            "total_spent": 0,
            "purchases_count": 0,
        }


async def get_group_statistics(head_name: str, stp_repo: MainRequestsRepo) -> dict:
    """Получить общую статистику группы руководителя"""
    try:
        # Получаем сотрудников группы
        group_users = await stp_repo.employee.get_users_by_head(head_name)

        total_points = 0
        group_purchases = {}

        for user in group_users:
            if user.user_id:  # Только авторизованные пользователи
                # Суммируем очки
                achievements_sum = await stp_repo.transaction.get_user_achievements_sum(
                    user.user_id
                )
                total_points += achievements_sum

                # Собираем статистику предметов
                most_bought_product = await stp_repo.purchase.get_most_bought_product(
                    user.user_id
                )
                if most_bought_product:
                    product_name = most_bought_product[0]
                    product_count = most_bought_product[1]
                    group_purchases[product_name] = (
                        group_purchases.get(product_name, 0) + product_count
                    )

        return {
            "total_users": len(group_users),
            "total_points": total_points,
        }
    except Exception as e:
        logger.error(f"Ошибка получения статистики группы {head_name}: {e}")
        return {
            "total_users": 0,
            "total_points": 0,
        }


async def get_group_statistics_by_id(
    head_user_id: int, stp_repo: MainRequestsRepo
) -> dict:
    """Получить общую статистику группы руководителя по его ID"""
    try:
        # Получаем руководителя по ID
        head_user = await stp_repo.employee.get_user(user_id=head_user_id)
        if not head_user:
            return {
                "total_users": 0,
                "total_points": 0,
                "most_popular_achievement": None,
                "most_popular_product": None,
            }

        # Используем существующую функцию
        return await get_group_statistics(head_user.fullname, stp_repo)
    except Exception as e:
        logger.error(f"Ошибка получения статистики группы по ID {head_user_id}: {e}")
        return {
            "total_users": 0,
            "total_points": 0,
            "most_popular_achievement": None,
            "most_popular_product": None,
        }


@mip_search_router.callback_query(MainMenu.filter(F.menu == "search"))
async def search_main_menu(callback: CallbackQuery, state: FSMContext):
    """Главное меню поиска сотрудников"""
    await state.clear()
    await callback.message.edit_text(
        """<b>🕵🏻 Поиск сотрудника</b>

<i>Выбери должность искомого человека или воспользуйся общим поиском</i>""",
        reply_markup=search_main_kb(),
    )


@mip_search_router.callback_query(SearchMenu.filter(F.menu == "specialists"))
async def show_specialists(
    callback: CallbackQuery, callback_data: SearchMenu, stp_repo: MainRequestsRepo
):
    """Показать всех специалистов с пагинацией"""
    page = callback_data.page

    # Получаем всех пользователей и фильтруем специалистов
    all_users = await stp_repo.employee.get_users()
    if not all_users:
        await callback.answer("❌ Пользователи не найдены", show_alert=True)
        return

    specialists = filter_users_by_type(all_users, "specialists")

    if not specialists:
        await callback.answer("❌ Специалисты не найдены", show_alert=True)
        return

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
        reply_markup=search_results_kb(page_users, page, total_pages, "specialists"),
    )


@mip_search_router.callback_query(SearchMenu.filter(F.menu == "heads"))
async def show_heads(
    callback: CallbackQuery, callback_data: SearchMenu, stp_repo: MainRequestsRepo
):
    """Показать всех руководителей с пагинацией"""
    page = callback_data.page

    # Получаем всех пользователей и фильтруем руководителей
    all_users = await stp_repo.employee.get_users()
    if not all_users:
        await callback.answer("❌ Пользователи не найдены", show_alert=True)
        return

    heads = filter_users_by_type(all_users, "heads")

    if not heads:
        await callback.answer("❌ Руководители не найдены", show_alert=True)
        return

    # Пагинация
    total_users = len(heads)
    total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE

    start_idx = (page - 1) * USERS_PER_PAGE
    end_idx = start_idx + USERS_PER_PAGE
    page_users = heads[start_idx:end_idx]

    await callback.message.edit_text(
        f"""<b>👑 Руководители</b>

Найдено руководителей: {total_users}
Страница {page} из {total_pages}

<i>💡 Нажми на руководителя, чтобы увидеть его группу</i>""",
        reply_markup=search_results_kb(page_users, page, total_pages, "heads"),
    )


@mip_search_router.callback_query(SearchMenu.filter(F.menu == "start_search"))
async def start_search(callback: CallbackQuery, state: FSMContext):
    """Начать поиск по имени"""
    bot_message = await callback.message.edit_text(
        """<b>🔍 Поиск сотрудника</b>

Введи часть имени, фамилии или полное ФИО сотрудника:

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
        reply_markup=search_back_kb(),
    )

    await state.update_data(bot_message_id=bot_message.message_id)
    await state.set_state(SearchEmployee.waiting_search_query)


@mip_search_router.message(SearchEmployee.waiting_search_query)
async def process_search_query(
    message: Message, state: FSMContext, stp_repo: MainRequestsRepo
):
    """Обработка поискового запроса"""
    search_query = message.text.strip()
    state_data = await state.get_data()
    bot_message_id = state_data.get("bot_message_id")

    # Удаляем сообщение пользователя
    await message.delete()

    if not search_query or len(search_query) < 2:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text="""<b>🔍 Поиск сотрудника</b>

❌ Поисковый запрос слишком короткий (минимум 2 символа)

Введи часть имени, фамилии или полное ФИО сотрудника:

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
            reply_markup=search_back_kb(),
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
                text=f"""<b>🔍 Поиск сотрудника</b>

❌ По запросу "<code>{search_query}</code>" ничего не найдено

Попробуй другой запрос или проверь правильность написания

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
                reply_markup=search_back_kb(),
            )
            return

        # Сортировка результатов (сначала точные совпадения)
        sorted_users = sorted(
            found_users,
            key=lambda u: (
                # Сначала полные совпадения
                search_query.lower() not in u.fullname.lower(),
                # Потом по алфавиту
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

По запросу "<code>{search_query}</code>" найдено: {total_found} сотрудников
Страница 1 из {total_pages}""",
            reply_markup=search_results_kb(
                page_users, 1, total_pages, "search_results"
            ),
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при поиске пользователей: {e}")
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text="""<b>🔍 Поиск сотрудника</b>

❌ Произошла ошибка при поиске. Попробуй позже

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
            reply_markup=search_back_kb(),
        )


@mip_search_router.callback_query(SearchUserResult.filter())
async def show_user_details(
    callback: CallbackQuery, callback_data: SearchUserResult, stp_repo: MainRequestsRepo
):
    """Показать детальную информацию о найденном пользователе"""
    user_id = callback_data.user_id
    return_to = callback_data.return_to
    head_id = callback_data.head_id

    try:
        user = await stp_repo.employee.get_user(user_id=user_id)
        user_head = await stp_repo.employee.get_user(fullname=user.head)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        if not user_head:
            await callback.answer(
                "❌ Не найдена информация о руководителя пользователя", show_alert=True
            )
            return

        # Определение роли
        role_name = role_names.get(user.role, "Неизвестная роль")

        # Получаем статистику пользователя
        stats = await get_user_statistics(user_id, stp_repo)

        # Формирование информации о пользователе
        user_info = f"""<b>👤 Информация о сотруднике</b>

<b>ФИО:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>Должность:</b> {user.position} {user.division}
<b>Руководитель:</b> <a href='t.me/{user_head.username}'>{user.head}</a>

🛡️<b>Уровень доступа:</b> {role_name} ({user.role})"""

        if user.email:
            user_info += f"\n<b>Рабочая почта:</b> {user.email}"

        # Добавляем статистику уровня (только для специалистов и дежурных)
        if user.user_id and user.role in [1, 3]:
            user_info += f"""

<blockquote expandable><b>📊 Статистика игрока</b>
<b>⚔️ Уровень:</b> {stats["level"]}
<b>✨ Баланс:</b> {stats["balance"]} баллов
<b>📈 Всего заработано:</b> {stats["total_earned"]} баллов
<b>💸 Всего потрачено:</b> {stats["total_spent"]} баллов</blockquote>"""

        # Дополнительная информация для руководителей
        if user.role == 2:  # Руководитель
            group_stats = await get_group_statistics(user.fullname, stp_repo)

            user_info += f"""

<blockquote expandable><b>👥 Статистика группы</b>
<b>Сотрудников в группе:</b> {group_stats["total_users"]}
<b>Общие очки группы:</b> {group_stats["total_points"]} баллов</blockquote>

<i>💡 Нажми кнопку ниже чтобы увидеть список группы</i>"""

        # Определяем возможность редактирования и параметры клавиатуры
        can_edit = user.role in [1, 2, 3]  # Специалисты, дежурные и руководители
        is_head = user.role == 2  # Руководитель
        head_user_id = user.user_id if is_head else 0

        await callback.message.edit_text(
            user_info,
            reply_markup=user_detail_kb(
                user_id, return_to, head_id, can_edit, is_head, head_user_id
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при получении информации о пользователе: {e}")
        await callback.answer("❌ Ошибка при получении данных", show_alert=True)


@mip_search_router.callback_query(HeadGroupMenu.filter())
async def show_head_group(
    callback: CallbackQuery, callback_data: HeadGroupMenu, stp_repo: MainRequestsRepo
):
    """Показать группу руководителя (список его сотрудников) с использованием функциональности head group members"""
    head_id = callback_data.head_id
    page = callback_data.page

    try:
        # Получаем информацию о руководителе по user_id
        head_user = await stp_repo.employee.get_user(user_id=head_id)
        if not head_user:
            await callback.answer("❌ Руководитель не найден", show_alert=True)
            return

        # Получаем всех сотрудников этого руководителя
        group_members = await stp_repo.employee.get_users_by_head(head_user.fullname)

        if not group_members:
            await callback.message.edit_text(
                f"""👥 <b>Группа: {head_user.fullname}</b>

У этого руководителя пока нет подчиненных в системе
            
<i>Если это ошибка, обратись к администратору.</i>""",
                reply_markup=head_group_members_kb_for_search(
                    [], current_page=1, head_id=head_id
                ),
            )
            return

        # Показываем группу с использованием того же стиля, что и в head group members
        total_members = len(group_members)

        message_text = f"""👥 <b>Группа: {head_user.fullname}</b>

Участники группы: <b>{total_members}</b>

<blockquote><b>Обозначения</b>
🔒 - не авторизован в боте
👮 - дежурный
🔨 - root</blockquote>

<i>Нажми на участника для просмотра подробной информации</i>"""

        await callback.message.edit_text(
            message_text,
            reply_markup=head_group_members_kb_for_search(
                group_members, current_page=page, head_id=head_id
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при получении группы руководителя {head_id}: {e}")
        await callback.answer("❌ Ошибка при получении данных группы", show_alert=True)


@mip_search_router.callback_query(EditUserMenu.filter())
async def start_edit_user(
    callback: CallbackQuery,
    callback_data: EditUserMenu,
    state: FSMContext,
    stp_repo: MainRequestsRepo,
):
    """Начать редактирование данных пользователя"""
    user_id = callback_data.user_id
    action = callback_data.action

    if action == "edit_fullname":
        # Получаем текущие данные пользователя
        user = await stp_repo.employee.get_user(user_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        bot_message = await callback.message.edit_text(
            f"""<b>✏️ Изменение ФИО</b>

<b>Текущее ФИО:</b> {user.fullname}

Введи новое ФИО:

<i>Например: Иванов Иван Иванович</i>""",
            reply_markup=edit_user_back_kb(user_id),
        )

        await state.update_data(
            bot_message_id=bot_message.message_id,
            user_id=user_id,
            current_fullname=user.fullname,
        )
        await state.set_state(EditEmployee.waiting_new_fullname)

    elif action == "edit_role":
        # Получаем текущие данные пользователя
        user = await stp_repo.employee.get_user(user_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Получаем название текущей роли
        current_role_name = (
            role_names[user.role]
            if user.role < len(role_names)
            else f"Неизвестная роль ({user.role})"
        )

        await callback.message.edit_text(
            f"""🛡️ <b>Изменение уровня доступа</b>

<b>Сотрудник:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>Текущий уровень доступа:</b> {current_role_name}

Выбери новую уровень для пользователя:

<i>Пользователь получит уведомление об изменении</i>""",
            reply_markup=role_selection_kb(user_id, user.role),
        )


@mip_search_router.message(EditEmployee.waiting_new_fullname)
async def process_edit_fullname(
    message: Message, state: FSMContext, stp_repo: MainRequestsRepo
):
    """Обработка изменения ФИО пользователя"""
    import re

    new_fullname = message.text.strip()
    state_data = await state.get_data()
    bot_message_id = state_data.get("bot_message_id")
    user_id = state_data.get("user_id")
    current_fullname = state_data.get("current_fullname")

    # Удаляем сообщение пользователя
    await message.delete()

    # Валидация ФИО
    fullname_pattern = r"^[А-Яа-яЁё]+ [А-Яа-яЁё]+ [А-Яа-яЁё]+$"
    if not re.match(fullname_pattern, new_fullname):
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text=f"""<b>✏️ Изменение ФИО</b>

<b>Текущее ФИО:</b> {current_fullname}

❌ Неверный формат ФИО. Попробуй ещё раз:

<i>Например: Иванов Иван Иванович</i>""",
            reply_markup=edit_user_back_kb(user_id),
        )
        return

    try:
        # Обновляем ФИО в базе данных
        await stp_repo.employee.update_user(user_id=user_id, fullname=new_fullname)

        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text=f"""<b>✅ ФИО изменено</b>

<b>Было:</b> <code>{current_fullname}</code>
<b>Стало:</b> <code>{new_fullname}</code>

Изменения сохранены в базе данных.""",
            reply_markup=edit_user_back_kb(user_id),
        )

        await state.clear()
        logger.info(
            f"[МИП] - [Изменение ФИО] {message.from_user.username} ({message.from_user.id}) изменил ФИО пользователя {user_id}: {current_fullname} → {new_fullname}"
        )

    except Exception as e:
        logger.error(f"Ошибка при изменении ФИО пользователя {user_id}: {e}")
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text=f"""<b>✏️ Изменение ФИО</b>

❌ Произошла ошибка при сохранении. Попробуй позже

<b>Текущее ФИО:</b> {current_fullname}""",
            reply_markup=edit_user_back_kb(user_id),
        )


@mip_search_router.callback_query(ViewUserSchedule.filter())
async def view_user_schedule(
    callback: CallbackQuery,
    callback_data: ViewUserSchedule,
    stp_repo: MainRequestsRepo,
):
    """Просмотр расписания пользователя"""
    user_id = callback_data.user_id
    return_to = callback_data.return_to
    head_id = callback_data.head_id
    requested_month_idx = callback_data.month_idx

    try:
        # Получаем пользователя
        user = await stp_repo.employee.get_user(user_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Определяем месяц для отображения
        if requested_month_idx > 0:
            current_month = get_month_name_by_index(requested_month_idx)
        else:
            current_month = schedule_service.get_current_month()

        try:
            # Получаем расписание пользователя (компактный формат) с дежурствами
            schedule_response = await schedule_service.get_user_schedule_response(
                user=user, month=current_month, compact=True, stp_repo=stp_repo
            )

            await callback.message.edit_text(
                f"""<b>📅 График сотрудника</b>

<b>ФИО:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>Подразделение:</b> {user.position or "Не указано"} {user.division or "Не указано"}

<blockquote>{schedule_response}</blockquote>""",
                reply_markup=user_schedule_with_month_kb(
                    user_id=user_id,
                    current_month=current_month,
                    return_to=return_to,
                    head_id=head_id,
                    is_detailed=False,
                ),
            )

        except Exception as schedule_error:
            # Если не удалось получить расписание, показываем ошибку
            error_message = "❌ График для данного сотрудника не найдено"
            if "не найден" in str(schedule_error).lower():
                error_message = f"❌ Сотрудник {user.fullname} не найден в графике"
            elif "файл" in str(schedule_error).lower():
                error_message = "❌ Файл графика недоступен"

            await callback.message.edit_text(
                f"""<b>📅 График сотрудника</b>

<b>ФИО:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>Подразделение:</b> {user.position or "Не указано"} {user.division or "Не указано"}

{error_message}

<i>Возможно, сотрудник не включен в текущий график или файл недоступен.</i>""",
                reply_markup=user_schedule_with_month_kb(
                    user_id=user_id,
                    current_month=current_month,
                    return_to=return_to,
                    head_id=head_id,
                    is_detailed=False,
                ),
            )

    except Exception as e:
        logger.error(f"Ошибка при получении расписания пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при получении расписания", show_alert=True)


@mip_search_router.callback_query(MipScheduleNavigation.filter())
async def navigate_user_schedule(
    callback: CallbackQuery,
    callback_data: MipScheduleNavigation,
    stp_repo: MainRequestsRepo,
):
    """Навигация по месяцам в расписании пользователя"""
    user_id = callback_data.user_id
    action = callback_data.action
    month_idx = callback_data.month_idx
    return_to = callback_data.return_to
    head_id = callback_data.head_id

    try:
        # Получаем пользователя
        user = await stp_repo.employee.get_user(user_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Определяем компактность вывода
        compact = action not in ["detailed"]

        # Преобразуем индекс месяца в название
        month_to_display = get_month_name_by_index(month_idx)

        try:
            # Получаем расписание пользователя с дежурствами
            schedule_response = await schedule_service.get_user_schedule_response(
                user=user, month=month_to_display, compact=compact, stp_repo=stp_repo
            )

            await callback.message.edit_text(
                f"""<b>📅 График сотрудника</b>

<b>ФИО:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>Подразделение:</b> {user.position or "Не указано"} {user.division or "Не указано"}

<blockquote>{schedule_response}</blockquote>""",
                reply_markup=user_schedule_with_month_kb(
                    user_id=user_id,
                    current_month=month_to_display,
                    return_to=return_to,
                    head_id=head_id,
                    is_detailed=not compact,
                ),
            )

        except Exception as schedule_error:
            # Если не удалось получить расписание, показываем ошибку
            error_message = "❌ График для данного сотрудника не найдено"
            if "не найден" in str(schedule_error).lower():
                error_message = f"❌ Сотрудник {user.fullname} не найден в графике"
            elif "файл" in str(schedule_error).lower():
                error_message = "❌ Файл графика недоступен"

            await callback.message.edit_text(
                f"""<b>📅 График сотрудника</b>

<b>ФИО:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>Подразделение:</b> {user.position or "Не указано"} {user.division or "Не указано"}

{error_message}

<i>Возможно, сотрудник не включен в текущий график или файл недоступен.</i>""",
                reply_markup=user_schedule_with_month_kb(
                    user_id=user_id,
                    current_month=month_to_display,
                    return_to=return_to,
                    head_id=head_id,
                    is_detailed=not compact,
                ),
            )

    except Exception as e:
        logger.error(f"Ошибка при навигации по расписанию пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при получении расписания", show_alert=True)


@mip_search_router.callback_query(SelectUserRole.filter())
async def process_role_change(
    callback: CallbackQuery, callback_data: SelectUserRole, stp_repo: MainRequestsRepo
):
    """Обработка изменения роли пользователя"""
    user_id = callback_data.user_id
    new_role = callback_data.role

    try:
        # Получаем данные пользователя
        user = await stp_repo.employee.get_user(user_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Проверяем, что роль действительно изменилась
        if user.role == new_role:
            await callback.answer("❌ Пользователь уже имеет эту роль", show_alert=True)
            return

        # Получаем названия ролей
        old_role_name = (
            role_names[user.role]
            if user.role < len(role_names)
            else f"Неизвестный уровень ({user.role})"
        )
        new_role_name = (
            role_names[new_role]
            if new_role < len(role_names)
            else f"Неизвестный уровень ({new_role})"
        )

        # Обновляем роль в базе данных
        await stp_repo.employee.update_user(user_id=user_id, role=new_role)

        # Отправляем уведомление пользователю о смене роли
        try:
            await callback.bot.send_message(
                chat_id=user_id,
                text=f"""<b>🔔 Изменение роли</b>

Уровень был изменен: {old_role_name} → {new_role_name}

<i>Изменения могут повлиять на доступные функции бота</i>""",
            )
        except Exception as notify_error:
            logger.error(
                f"Не удалось отправить уведомление пользователю {user_id}: {notify_error}"
            )

        logger.info(
            f"[МИП] - [Изменение роли] {callback.from_user.username} ({callback.from_user.id}) изменил роль пользователя {user_id}: {old_role_name} → {new_role_name}"
        )

        # Возвращаемся к информации о пользователе
        # Создаем новый callback_data для возврата к пользователю
        user_callback_data = SearchUserResult(user_id=user_id)
        await show_user_details(callback, user_callback_data, stp_repo)

    except Exception as e:
        logger.error(f"Ошибка при изменении роли пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при сохранении роли", show_alert=True)


# Обработчики для search-специфичных callback data (для интеграции с head group members)


@mip_search_router.callback_query(HeadGroupMembersMenuForSearch.filter())
async def group_members_pagination_cb_search(
    callback: CallbackQuery,
    callback_data: HeadGroupMembersMenuForSearch,
    stp_repo: MainRequestsRepo,
):
    """Обработчик пагинации списка участников группы из поиска"""
    head_id = callback_data.head_id
    page = callback_data.page

    try:
        # Получаем информацию о руководителе
        head_user = await stp_repo.employee.get_user(user_id=head_id)
        if not head_user:
            await callback.answer("❌ Руководитель не найден", show_alert=True)
            return

        # Получаем всех сотрудников этого руководителя
        group_members = await stp_repo.employee.get_users_by_head(head_user.fullname)

        if not group_members:
            await callback.answer("❌ Участники не найдены", show_alert=True)
            return

        total_members = len(group_members)

        message_text = f"""👥 <b>Группа: {head_user.fullname}</b>

Участники группы: <b>{total_members}</b>

<blockquote><b>Обозначения</b>
🔒 - не авторизован в боте
👮 - дежурный
🔨 - root</blockquote>

<i>Нажми на участника для просмотра подробной информации</i>"""

        await callback.message.edit_text(
            message_text,
            reply_markup=head_group_members_kb_for_search(
                group_members, current_page=page, head_id=head_id
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при пагинации группы руководителя {head_id}: {e}")
        await callback.answer("❌ Ошибка при получении данных", show_alert=True)


@mip_search_router.callback_query(HeadMemberDetailMenuForSearch.filter())
async def member_detail_cb_search(
    callback: CallbackQuery,
    callback_data: HeadMemberDetailMenuForSearch,
    stp_repo: MainRequestsRepo,
):
    """Обработчик детального просмотра участника группы из поиска"""
    member_id = callback_data.member_id
    head_id = callback_data.head_id
    page = callback_data.page

    try:
        # Поиск участника по ID
        all_users = await stp_repo.employee.get_users()
        member = None
        for user in all_users:
            if user.id == member_id:
                member = user
                break

        if not member:
            await callback.answer("❌ Участник не найден", show_alert=True)
            return

        # Импортируем get_role_info из группового модуля
        from tgbot.handlers.group.whois import get_role_info

        # Формируем информацию об участнике
        message_text = f"""👤 <b>Информация об участнике</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}
<b>Email:</b> {member.email or "Не указано"}

🛡️ <b>Уровень доступа:</b> <code>{get_role_info(member.role)["text"]}</code>"""

        # Добавляем статус только для неавторизованных пользователей
        if not member.user_id:
            message_text += "\n<b>Статус:</b> 🔒 Не авторизован в боте"

        message_text += "\n\n<i>Выбери действие:</i>"

        await callback.message.edit_text(
            message_text,
            reply_markup=head_member_detail_kb_for_search(
                member_id, head_id, page, member.role
            ),
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Ошибка при просмотре участника {member_id}: {e}")
        await callback.answer(
            "❌ Ошибка при получении данных участника", show_alert=True
        )


@mip_search_router.callback_query(HeadMemberActionMenuForSearch.filter())
async def member_action_cb_search(
    callback: CallbackQuery,
    callback_data: HeadMemberActionMenuForSearch,
    stp_repo: MainRequestsRepo,
):
    """Обработчик действий с участником (расписание/KPI/игра) из поиска"""
    member_id = callback_data.member_id
    head_id = callback_data.head_id
    action = callback_data.action
    page = callback_data.page

    try:
        # Поиск участника по ID
        all_users = await stp_repo.employee.get_users()
        member = None
        for user in all_users:
            if user.id == member_id:
                member = user
                break

        if not member:
            await callback.answer("❌ Участник не найден", show_alert=True)
            return

        if action == "schedule":
            # Используем существующую логику из head group members для расписания
            try:
                current_month = schedule_service.get_current_month()
                schedule_response = await schedule_service.get_user_schedule_response(
                    user=member, month=current_month, compact=True, stp_repo=stp_repo
                )

                await callback.message.edit_text(
                    f"""📅 <b>График участника</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or "Не указано"}

<blockquote>{schedule_response}</blockquote>""",
                    reply_markup=head_member_detail_kb_for_search(
                        member_id, head_id, page, member.role
                    ),
                )
            except Exception as schedule_error:
                error_message = "❌ График для данного сотрудника не найдено"
                if "не найден" in str(schedule_error).lower():
                    error_message = (
                        f"❌ Сотрудник {member.fullname} не найден в графике"
                    )
                elif "файл" in str(schedule_error).lower():
                    error_message = "❌ Файл графика недоступен"

                await callback.message.edit_text(
                    f"""📅 <b>График участника</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or "Не указано"}

{error_message}

<i>Возможно, сотрудник не включен в текущий график или файл недоступен.</i>""",
                    reply_markup=head_member_detail_kb_for_search(
                        member_id, head_id, page, member.role
                    ),
                )
            return

        elif action == "kpi":
            message_text = f"""📊 <b>KPI: {member.fullname}</b>

<i>Функция в разработке</i>

Здесь будут отображены показатели эффективности выбранного сотрудника."""

            await callback.message.edit_text(
                message_text,
                reply_markup=head_member_detail_kb_for_search(
                    member_id, head_id, page, member.role
                ),
            )
            return

        elif action == "game_profile":
            # Проверяем, что у участника есть user_id (авторизован в боте)
            if not member.user_id:
                await callback.message.edit_text(
                    f"""🏮 <b>Игровой профиль</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>

❌ <b>Пользователь не авторизован в боте</b>

<i>Игровой профиль доступен только для авторизованных пользователей</i>""",
                    reply_markup=head_member_detail_kb_for_search(
                        member_id, head_id, page, member.role
                    ),
                    parse_mode="HTML",
                )
                return

            # Получаем игровую статистику пользователя
            from tgbot.services.leveling import LevelingSystem

            user_balance = await stp_repo.transaction.get_user_balance(
                user_id=member.user_id
            )
            achievements_sum = await stp_repo.transaction.get_user_achievements_sum(
                user_id=member.user_id
            )
            purchases_sum = await stp_repo.purchase.get_user_purchases_sum(
                user_id=member.user_id
            )
            level_info_text = LevelingSystem.get_level_info_text(
                achievements_sum, user_balance
            )

            # Формируем сообщение с игровым профилем
            message_text = f"""🏮 <b>Игровой профиль</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}

{level_info_text}

<blockquote expandable><b>✨ Баланс</b>
Всего заработано: {achievements_sum} баллов
Всего потрачено: {purchases_sum} баллов</blockquote>"""

            await callback.message.edit_text(
                message_text,
                reply_markup=head_member_detail_kb_for_search(
                    member_id, head_id, page, member.role
                ),
                parse_mode="HTML",
            )
            return

        else:
            await callback.answer("❌ Неизвестное действие", show_alert=True)
            return

    except Exception as e:
        logger.error(
            f"Ошибка при выполнении действия {action} для участника {member_id}: {e}"
        )
        await callback.answer("❌ Ошибка при выполнении действия", show_alert=True)


@mip_search_router.callback_query(HeadMemberRoleChangeForSearch.filter())
async def change_member_role_search(
    callback: CallbackQuery,
    callback_data: HeadMemberRoleChangeForSearch,
    stp_repo: MainRequestsRepo,
):
    """Обработчик смены роли участника группы из поиска"""
    member_id = callback_data.member_id
    head_id = callback_data.head_id
    page = callback_data.page

    try:
        # Поиск участника по ID
        all_users = await stp_repo.employee.get_users()
        member = None
        for user in all_users:
            if user.id == member_id:
                member = user
                break

        if not member:
            await callback.answer("❌ Участник не найден", show_alert=True)
            return

        # Проверяем, что роль может быть изменена
        if member.role not in [1, 3]:
            await callback.answer(
                "❌ Уровень доступа этого пользователя нельзя изменить", show_alert=True
            )
            return

        # Определяем новый уровень доступа
        new_role = 3 if member.role == 1 else 1
        old_role_name = "Специалист" if member.role == 1 else "Дежурный"
        new_role_name = "Дежурный" if new_role == 3 else "Специалист"

        # Обновляем уровень в базе данных
        await stp_repo.employee.update_user(user_id=member.user_id, role=new_role)

        # Отправляем уведомление пользователю о смене роли (только если он авторизован)
        if member.user_id:
            try:
                await callback.bot.send_message(
                    chat_id=member.user_id,
                    text=f"""<b>🔔 Изменение роли</b>

Уровень был изменен: {old_role_name} → {new_role_name}

<i>Изменения могут повлиять на доступные функции бота</i>""",
                )
                await callback.answer(
                    "Отправили специалисту уведомление об изменении роли"
                )
            except Exception as e:
                await callback.answer("Не удалось отправить уведомление специалисту :(")
                logger.error(
                    f"Не удалось отправить уведомление пользователю {member.user_id}: {e}"
                )

        logger.info(
            f"[МИП] - [Изменение роли] {callback.from_user.username} ({callback.from_user.id}) изменил роль участника {member_id}: {old_role_name} → {new_role_name}"
        )

        # Возвращаемся к детальной информации участника
        member_detail_callback_data = HeadMemberDetailMenuForSearch(
            member_id=member_id, head_id=head_id, page=page
        )
        await member_detail_cb_search(callback, member_detail_callback_data, stp_repo)

    except Exception as e:
        logger.error(f"Ошибка при изменении роли участника {member_id}: {e}")
        await callback.answer("❌ Ошибка при изменении роли", show_alert=True)
