import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.leveling.main import (
    AwardActionMenu,
    AwardActivationMenu,
    AwardsMenu,
    FilterToggleMenu,
    LevelingMenu,
    achievements_kb,
    achievements_paginated_kb,
    award_activation_kb,
    award_detail_kb,
    awards_paginated_kb,
    parse_filters,
    toggle_filter,
)
from tgbot.keyboards.user.main import MainMenu

mip_leveling_router = Router()
mip_leveling_router.message.filter(F.chat.type == "private", MipFilter())
mip_leveling_router.callback_query.filter(F.message.chat.type == "private", MipFilter())

logger = logging.getLogger(__name__)


def filter_items_by_division(items, active_filters):
    """Filter achievements or awards by division based on active filters"""
    # Filter by specific divisions
    filtered_items = []
    for item in items:
        if item.division in active_filters:
            filtered_items.append(item)

    return filtered_items


@mip_leveling_router.callback_query(MainMenu.filter(F.menu == "leveling"))
async def mip_achievements_cmd(callback: CallbackQuery):
    await callback.message.edit_text(
        """<b>🏆 Ачивки</b>

Здесь ты можешь:
- Подтверждать/отклонять награды специалистов
- Просматривать список достижений
- Просматривать список наград""",
        reply_markup=achievements_kb(),
    )


@mip_leveling_router.callback_query(LevelingMenu.filter(F.menu == "achievements_all"))
async def achievements_all(
    callback: CallbackQuery, callback_data: LevelingMenu, stp_repo: RequestsRepo
):
    """
    Обработчик клика на меню всех возможных достижений для МИП
    МИП видит все достижения из всех направлений с возможностью фильтрации
    """

    # Достаём параметры из callback data
    page = getattr(callback_data, "page", 1)
    filters = getattr(callback_data, "filters", "НЦК,НТП")

    # Парсим активные фильтры
    active_filters = parse_filters(filters)

    # Получаем ВСЕ достижения без фильтрации по направлению
    all_achievements = await stp_repo.achievement.get_achievements()

    # Применяем фильтрацию
    filtered_achievements = filter_items_by_division(all_achievements, active_filters)

    # Логика пагинации
    achievements_per_page = 5
    total_achievements = len(filtered_achievements)
    total_pages = (
        total_achievements + achievements_per_page - 1
    ) // achievements_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * achievements_per_page
    end_idx = start_idx + achievements_per_page
    page_achievements = filtered_achievements[start_idx:end_idx]

    # Построение списка достижений для текущей страницы
    achievements_list = []
    for counter, achievement in enumerate(page_achievements, start=start_idx + 1):
        # Экранируем HTML символы в полях
        description = (
            str(achievement.description).replace("<", "&lt;").replace(">", "&gt;")
        )
        name = str(achievement.name).replace("<", "&lt;").replace(">", "&gt;")
        division = str(achievement.division).replace("<", "&lt;").replace(">", "&gt;")
        position = str(achievement.position).replace("<", "&lt;").replace(">", "&gt;")

        achievements_list.append(f"""{counter}. <b>{name}</b>
🏅 Награда: {achievement.reward} баллов
📝 Описание: {description}
🔰 Должность: {position} {division}""")
        achievements_list.append("")

    # Создаем статистику по всем достижениям (не только отфильтрованным)
    stats_ntp = sum(
        1 for achievement in all_achievements if achievement.division == "НТП"
    )
    stats_nck = sum(
        1 for achievement in all_achievements if achievement.division == "НЦК"
    )

    # Статистика по отфильтрованным
    filtered_stats = f"Показано: {total_achievements}"

    message_text = f"""<b>🎯 Все возможные достижения</b>
<i>Страница {page} из {total_pages}</i>

<blockquote>Всего достижений:
НТП: {stats_ntp} | НЦК: {stats_nck}
{filtered_stats}</blockquote>

{chr(10).join(achievements_list)}"""

    await callback.message.edit_text(
        message_text, reply_markup=achievements_paginated_kb(page, total_pages, filters)
    )
    logger.info(
        f"[МИП] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыто меню всех достижений, страница {page}, фильтры: {filters}"
    )


@mip_leveling_router.callback_query(AwardsMenu.filter(F.menu == "awards_all"))
async def awards_all(
    callback: CallbackQuery, callback_data: AwardsMenu, stp_repo: RequestsRepo
):
    """
    Обработчик клика на меню всех возможных наград для МИП
    МИП видит все награды из всех направлений с возможностью фильтрации
    """

    # Достаём параметры из callback data
    page = getattr(callback_data, "page", 1)
    filters = getattr(callback_data, "filters", "НЦК,НТП")

    # Парсим активные фильтры
    active_filters = parse_filters(filters)

    # Получаем ВСЕ награды без фильтрации по направлению
    all_awards = await stp_repo.award.get_awards()

    # Применяем фильтрацию
    filtered_awards = filter_items_by_division(all_awards, active_filters)

    # Логика пагинации
    awards_per_page = 5
    total_awards = len(filtered_awards)
    total_pages = (total_awards + awards_per_page - 1) // awards_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * awards_per_page
    end_idx = start_idx + awards_per_page
    page_awards = filtered_awards[start_idx:end_idx]

    # Построение списка наград для текущей страницы
    awards_list = []
    for counter, award in enumerate(page_awards, start=start_idx + 1):
        award_text = f"""
<b>{counter}. {award.name}</b>
📍 Активаций: {award.count}
💵 Стоимость: {award.cost} баллов
🔰 Направление: {award.division}
📝 Описание: {award.description}"""
        awards_list.append(award_text)

    # Статистика
    stats_ntp = sum(1 for award in all_awards if award.division == "НТП")
    stats_nck = sum(1 for award in all_awards if award.division == "НЦК")
    filtered_stats = f"Показано: {total_awards}"

    message_text = f"""
<b>🏆 Все возможные награды</b>
<i>Страница {page} из {total_pages}</i>

<blockquote expandable>
Всего наград:  
• НТП: {stats_ntp}  
• НЦК: {stats_nck}  
{filtered_stats}
</blockquote>

    {chr(10).join(awards_list)}
    """

    await callback.message.edit_text(
        message_text, reply_markup=awards_paginated_kb(page, total_pages, filters)
    )
    logger.info(
        f"[МИП] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыто меню всех наград, страница {page}, фильтры: {filters}"
    )


@mip_leveling_router.callback_query(LevelingMenu.filter(F.menu == "awards_activation"))
async def awards_activation(
    callback: CallbackQuery, callback_data: LevelingMenu, stp_repo: RequestsRepo
):
    """
    Обработчик меню наград для активации
    Показывает награды со статусом "review" и manager_role == 6
    """

    # Достаём номер страницы из callback data, стандартно = 1
    page = getattr(callback_data, "page", 1)

    # Получаем награды ожидающие активации с manager_role == 6
    review_awards = await stp_repo.user_award.get_review_awards_for_activation(
        manager_role=6
    )

    if not review_awards:
        await callback.message.edit_text(
            """<b>✍️ Награды для активации</b>

Нет наград, ожидающих активации 😊""",
            reply_markup=award_activation_kb(page, 0, []),
        )
        return

    # Логика пагинации
    awards_per_page = 5
    total_awards = len(review_awards)
    total_pages = (total_awards + awards_per_page - 1) // awards_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * awards_per_page
    end_idx = start_idx + awards_per_page
    page_awards = review_awards[start_idx:end_idx]

    # Построение списка наград для текущей страницы
    awards_list = []
    for counter, award_detail in enumerate(page_awards, start=start_idx + 1):
        user_award = award_detail.user_award
        award_info = award_detail.award_info

        # Получаем информацию о пользователе
        user = await stp_repo.user.get_user(user_id=user_award.user_id)
        user_name = user.fullname if user else f"ID: {user_award.user_id}"

        if user.username:
            awards_list.append(f"""{counter}. <b>{award_info.name}</b> - {user_award.bought_at.strftime("%d.%m.%Y в %H:%M")}
<blockquote><b>👤 Специалист</b>
<a href='t.me/{user.username}'>{user_name}</a> из {award_info.division}

<b>📝 Описание</b>
{award_info.description}</blockquote>""")
        else:
            awards_list.append(f"""{counter}. <b>{award_info.name}</b> - {user_award.bought_at.strftime("%d.%m.%Y в %H:%M")}
<blockquote><b>👤 Специалист</b>
<a href='tg://user?id={user.user_id}'>{user_name}</a> из {award_info.division}

<b>📝 Описание</b>
{award_info.description}</blockquote>""")
        awards_list.append("")

    message_text = f"""<b>✍️ Награды для активации</b>
<i>Страница {page} из {total_pages}</i>

{chr(10).join(awards_list)}"""

    await callback.message.edit_text(
        message_text, reply_markup=award_activation_kb(page, total_pages, page_awards)
    )


@mip_leveling_router.callback_query(AwardActivationMenu.filter())
async def award_activation_detail(
    callback: CallbackQuery, callback_data: AwardActivationMenu, stp_repo: RequestsRepo
):
    """Показывает детальную информацию о награде для активации"""
    user_award_id = callback_data.user_award_id
    current_page = callback_data.page

    # Получаем информацию о конкретной награде
    user_award_detail = await stp_repo.user_award.get_user_award_detail(user_award_id)

    if not user_award_detail:
        await callback.message.edit_text(
            """<b>✍️ Активация награды</b>

Не смог найти описание для награды ☹""",
            reply_markup=award_detail_kb(user_award_id, current_page),
        )
        return

    user_award = user_award_detail.user_award
    award_info = user_award_detail.award_info

    # Получаем информацию о пользователе
    user: User = await stp_repo.user.get_user(user_id=user_award.user_id)
    user_head: User = await stp_repo.user.get_user(fullname=user.head)

    user_info = (
        f"<a href='t.me/{user.username}'>{user.fullname}</a>"
        if user and user.username
        else "-"
    )
    head_info = (
        f"<a href='t.me/{user_head.username}'>{user.head}</a>"
        if user_head and user_head.username
        else "-"
    )

    message_text = f"""
<b>🎯 Активация награды</b>

<b>🏆 О награде</b>  
<blockquote><b>Название</b>
{award_info.name}
  
<b>📝 Описание</b>
{award_info.description}

<b>💵 Стоимость</b>
{award_info.cost} баллов

<b>📍 Активаций</b>
{user_award.usage_count} ➡️ {user_award.usage_count + 1} ({award_info.count} всего)</blockquote>"""

    message_text += f"""

<b>👤 О специалисте</b>
<blockquote><b>ФИО</b>
{user_info}

<b>Должность</b>
{user.position} {user.division}

<b>Руководитель</b>
{head_info}</blockquote>

<b>📅 Дата покупки</b>  
{user_award.bought_at.strftime("%d.%m.%Y в %H:%M")}
"""
    await callback.message.edit_text(
        message_text,
        reply_markup=award_detail_kb(user_award_id, current_page),
    )


@mip_leveling_router.callback_query(AwardActionMenu.filter())
async def award_action(
    callback: CallbackQuery, callback_data: AwardActionMenu, stp_repo: RequestsRepo
):
    """Обработка подтверждения/отклонения награды"""
    user_award_id = callback_data.user_award_id
    action = callback_data.action
    current_page = callback_data.page

    try:
        # Получаем информацию о награде
        user_award_detail = await stp_repo.user_award.get_user_award_detail(
            user_award_id
        )

        if not user_award_detail:
            await callback.answer("❌ Награда не найдена", show_alert=True)
            return

        user_award = user_award_detail.user_award
        award_info = user_award_detail.award_info
        user = await stp_repo.user.get_user(user_id=user_award.user_id)

        if action == "approve":
            # Подтверждаем награду
            await stp_repo.user_award.approve_award_usage(
                user_award_id=user_award_id,
                updated_by_user_id=callback.from_user.id,
            )

            await callback.answer(
                f"✅ Награда '{award_info.name}' подтверждена!",
                show_alert=True,
            )

            logger.info(
                f"[МИП] - [Подтверждение] {callback.from_user.username} ({callback.from_user.id}) подтвердил награду {award_info.name} для пользователя {user.username} ({user_award.user_id})"
            )

        elif action == "reject":
            # Отклоняем награду
            # TODO изменить логику отмены. Информировать пользователя об отмене. Не прибавлять и не отменять использование награды
            await stp_repo.user_award.reject_award_usage(
                user_award_id=user_award_id, updated_by_user_id=callback.from_user.id
            )

            await callback.answer(
                f"❌ Награда '{award_info.name}' отклонена",
                show_alert=True,
            )

            logger.info(
                f"[МИП] - [Отклонение] {callback.from_user.username} ({callback.from_user.id}) отклонил награду {award_info.name} для пользователя {user.username} ({user_award.user_id})"
            )

        # Возвращаемся к списку наград для активации
        await awards_activation(
            callback=callback,
            callback_data=LevelingMenu(menu="awards_activation", page=current_page),
            stp_repo=stp_repo,
        )

    except Exception as e:
        logger.error(f"Error updating award status: {e}")
        await callback.answer("❌ Ошибка при обработке награды", show_alert=True)


@mip_leveling_router.callback_query(FilterToggleMenu.filter())
async def toggle_filter_handler(
    callback: CallbackQuery, callback_data: FilterToggleMenu, stp_repo: RequestsRepo
):
    """Обработчик переключения фильтров"""
    menu = callback_data.menu
    filter_name = callback_data.filter_name
    current_filters = callback_data.current_filters

    # Переключаем фильтр
    new_filters = toggle_filter(current_filters, filter_name)

    # Переходим на первую страницу при изменении фильтров
    if menu == "achievements_all":
        await achievements_all(
            callback,
            LevelingMenu(menu="achievements_all", page=1, filters=new_filters),
            stp_repo,
        )
    elif menu == "awards_all":
        await awards_all(
            callback,
            AwardsMenu(menu="awards_all", page=1, filters=new_filters),
            stp_repo,
        )
