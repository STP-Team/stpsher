import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import GokFilter
from tgbot.handlers.gok.leveling.main import filter_items_by_division
from tgbot.keyboards.gok.leveling.awards import (
    gok_award_activation_kb,
    gok_award_detail_kb,
    gok_awards_paginated_kb,
)
from tgbot.keyboards.gok.main import (
    parse_filters,
    GokAwardsMenu,
    GokLevelingMenu,
    GokAwardActivationMenu,
    GokAwardActionMenu,
)

gok_leveling_awards_router = Router()
gok_leveling_awards_router.message.filter(F.chat.type == "private", GokFilter())
gok_leveling_awards_router.callback_query.filter(
    F.message.chat.type == "private", GokFilter()
)

logger = logging.getLogger(__name__)


@gok_leveling_awards_router.callback_query(GokAwardsMenu.filter(F.menu == "awards_all"))
async def gok_awards_all(
    callback: CallbackQuery, callback_data: GokAwardsMenu, stp_repo: MainRequestsRepo
):
    """
    Обработчик клика на меню всех возможных наград для ГОК
    ГОК видит все награды из всех направлений с возможностью фильтрации
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

<blockquote expandable><b>Всего наград:</b>  
• НТП: {stats_ntp}  
• НЦК: {stats_nck}  
{filtered_stats}
</blockquote>{chr(10).join(awards_list)}
    """

    await callback.message.edit_text(
        message_text, reply_markup=gok_awards_paginated_kb(page, total_pages, filters)
    )
    logger.info(
        f"[ГОК] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыто меню всех наград, страница {page}, фильтры: {filters}"
    )


@gok_leveling_awards_router.callback_query(
    GokLevelingMenu.filter(F.menu == "awards_activation")
)
async def gok_awards_activation(
    callback: CallbackQuery, callback_data: GokLevelingMenu, stp_repo: MainRequestsRepo
):
    """
    Обработчик меню наград для активации
    Показывает награды со статусом "review" и manager_role == 5 (ГОК)
    """

    # Достаём номер страницы из callback data, стандартно = 1
    page = getattr(callback_data, "page", 1)

    # Получаем награды ожидающие активации с manager_role == 5 (ГОК)
    review_awards = await stp_repo.user_award.get_review_awards_for_activation(
        manager_role=5
    )

    if not review_awards:
        await callback.message.edit_text(
            """<b>✍️ Награды для активации</b>

Нет наград, ожидающих активации 😊""",
            reply_markup=gok_award_activation_kb(page, 0, []),
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
        message_text,
        reply_markup=gok_award_activation_kb(page, total_pages, page_awards),
    )


@gok_leveling_awards_router.callback_query(GokAwardActivationMenu.filter())
async def gok_award_activation_detail(
    callback: CallbackQuery,
    callback_data: GokAwardActivationMenu,
    stp_repo: MainRequestsRepo,
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
            reply_markup=gok_award_detail_kb(user_award_id, current_page),
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
        reply_markup=gok_award_detail_kb(user_award_id, current_page),
    )


@gok_leveling_awards_router.callback_query(GokAwardActionMenu.filter())
async def gok_award_action(
    callback: CallbackQuery,
    callback_data: GokAwardActionMenu,
    stp_repo: MainRequestsRepo,
    user: User,
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
        employee_user: User = await stp_repo.user.get_user(user_id=user_award.user_id)

        if action == "approve":
            # Подтверждаем награду
            await stp_repo.user_award.approve_award_usage(
                user_award_id=user_award_id,
                updated_by_user_id=callback.from_user.id,
            )

            await callback.answer(
                f"""✅ Награда '{award_info.name}' активирована!
                
Специалист {employee_user.fullname} был уведомлен об изменении статуса""",
                show_alert=True,
            )

            if user_award.usage_count >= award_info.count:
                employee_notify_message = f"""<b>👌 Награда активирована:</b> {award_info.name}

ГОК-менеджер <a href='t.me/{user.username}'>{user.fullname}</a> подтвердил активацию награды

У награды <b>{award_info.name}</b> не осталось использований 

<i>Купить награду повторно можно в меню <b>👏 Награды → ❇️ Доступные</b></i>"""
            else:
                employee_notify_message = f"""<b>👌 Награда активирована:</b> {award_info.name}

ГОК-менеджер <a href='t.me/{user.username}'>{user.fullname}</a> подтвердил активацию награды

📍 Осталось активаций: {award_info.count - user_award.usage_count} из {award_info.count}"""

            await callback.bot.send_message(
                chat_id=employee_user.user_id,
                text=employee_notify_message,
            )

            logger.info(
                f"[ГОК] - [Подтверждение] {callback.from_user.username} ({callback.from_user.id}) подтвердил награду {award_info.name} для пользователя {user.username} ({user_award.user_id})"
            )

        elif action == "reject":
            # Отклоняем награду
            await stp_repo.user_award.reject_award_usage(
                user_award_id=user_award_id, updated_by_user_id=callback.from_user.id
            )

            await callback.answer(
                f"""❌ Награда '{award_info.name}' отклонена

Специалист {employee_user.fullname} был уведомлен об изменении статуса""",
                show_alert=True,
            )

            await callback.bot.send_message(
                chat_id=employee_user.user_id,
                text=f"""<b>Активация отменена:</b> {award_info.name}

ГОК-менеджер <a href='t.me/{user.username}'>{user.fullname}</a> отменил активацию награды""",
            )

            logger.info(
                f"[ГОК] - [Отклонение] {callback.from_user.username} ({callback.from_user.id}) отклонил награду {award_info.name} для пользователя {employee_user.username} ({user_award.user_id})"
            )

        # Возвращаемся к списку наград для активации
        await gok_awards_activation(
            callback=callback,
            callback_data=GokLevelingMenu(menu="awards_activation", page=current_page),
            stp_repo=stp_repo,
        )

    except Exception as e:
        logger.error(f"Error updating award status: {e}")
        await callback.answer("❌ Ошибка при обработке награды", show_alert=True)
