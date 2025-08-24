import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.leveling.main import (
    AwardActionMenu,
    AwardActivationMenu,
    AwardsMenu,
    LevelingMenu,
    achievements_kb,
    achievements_paginated_kb,
    award_activation_kb,
    award_detail_kb,
    awards_paginated_kb,
)
from tgbot.keyboards.user.main import MainMenu

mip_leveling_router = Router()
mip_leveling_router.message.filter(F.chat.type == "private", MipFilter())
mip_leveling_router.callback_query.filter(F.message.chat.type == "private", MipFilter())

logger = logging.getLogger(__name__)


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


@mip_leveling_router.callback_query(LevelingMenu.filter(F.menu == "awards_activation"))
async def awards_activation(
    callback: CallbackQuery, callback_data: LevelingMenu, stp_repo: RequestsRepo
):
    """
    Обработчик меню наград для активации
    Показывает награды со статусом "waiting" и manager_role == 6
    """

    # Достаём номер страницы из callback data, стандартно = 1
    page = getattr(callback_data, "page", 1)

    # Получаем награды ожидающие активации с manager_role == 6
    waiting_awards = await stp_repo.user_award.get_waiting_awards_for_activation(
        manager_role=6
    )

    if not waiting_awards:
        await callback.message.edit_text(
            """<b>✍️ Награды для активации</b>

Нет наград, ожидающих активации 😊""",
            reply_markup=award_activation_kb(page, 0, []),
        )
        return

    # Логика пагинации
    awards_per_page = 5
    total_awards = len(waiting_awards)
    total_pages = (total_awards + awards_per_page - 1) // awards_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * awards_per_page
    end_idx = start_idx + awards_per_page
    page_awards = waiting_awards[start_idx:end_idx]

    # Построение списка наград для текущей страницы
    awards_list = []
    for counter, award_detail in enumerate(page_awards, start=start_idx + 1):
        user_award = award_detail.user_award
        award_info = award_detail.award_info

        # Получаем информацию о пользователе
        user = await stp_repo.user.get_user(user_id=user_award.user_id)
        user_name = user.fullname if user else f"ID: {user_award.user_id}"

        awards_list.append(f"""{counter}. <b>{award_info.name}</b>
👤 Специалист: <a href='tg://user?id={user.user_id}'>{user_name}</a>
💵 Стоимость: {award_info.cost} баллов
📅 Дата: {user_award.bought_at.strftime("%d.%m.%Y %H:%M")}""")
        awards_list.append("")

    message_text = f"""<b>✍️ Награды для активации</b>
<i>Страница {page} из {total_pages}</i>

<blockquote>Всего ожидает активации: {total_awards}</blockquote>

{"\n".join(awards_list)}"""

    await callback.message.edit_text(
        message_text, reply_markup=award_activation_kb(page, total_pages, page_awards)
    )
    logger.info(
        f"[МИП] - [Активация] {callback.from_user.username} ({callback.from_user.id}): Открыто меню активации наград, страница {page}"
    )


@mip_leveling_router.callback_query(AwardActivationMenu.filter())
async def award_activation_detail(
    callback: CallbackQuery, callback_data: AwardActivationMenu, stp_repo: RequestsRepo
):
    """
    Обработчик клика на конкретную награду для активации
    """
    user_award_id = callback_data.user_award_id
    current_page = callback_data.page

    # Получаем детальную информацию о награде
    award_detail = await stp_repo.user_award.get_user_award_detail(user_award_id)

    if not award_detail:
        await callback.answer("❌ Награда не найдена", show_alert=True)
        return

    user_award = award_detail.user_award
    award_info = award_detail.award_info

    # Получаем полную информацию о пользователе
    user = await stp_repo.user.get_user(user_id=user_award.user_id)

    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    # Формируем сообщение с полной информацией
    message_text = f"""<b>🎯 Активация награды</b>

<b>🏆 О награде:</b>
• Название: {award_info.name}
• Описание: {award_info.description}
• Стоимость: {award_info.cost} баллов
• Направление: {award_info.division}"""

    if award_info.count > 1:
        message_text += f"\n• Использований: {award_info.count}"

    message_text += f"""

<b>👤 О специалисте:</b>
• ФИО: <b>{user.fullname}</b>
• Направление: {user.division}
• Должность: {user.position}
• Руководитель: {user.head}

<b>📅 Дата покупки:</b> {user_award.bought_at.strftime("%d.%m.%Y в %H:%M")}"""

    if user_award.comment:
        message_text += f"\n<b>💬 Комментарий:</b> {user_award.comment}"

    await callback.message.edit_text(
        message_text,
        reply_markup=award_detail_kb(user_award_id, current_page, user.user_id),
    )


@mip_leveling_router.callback_query(AwardActionMenu.filter())
async def award_action_handler(
    callback: CallbackQuery, callback_data: AwardActionMenu, stp_repo: RequestsRepo
):
    """
    Обработчик действий одобрения/отклонения награды
    """
    user_award_id = callback_data.user_award_id
    action = callback_data.action
    current_page = callback_data.page

    # Получаем информацию о награде
    award_detail = await stp_repo.user_award.get_user_award_detail(user_award_id)

    if not award_detail:
        await callback.answer("❌ Награда не найдена", show_alert=True)
        return

    user_award = award_detail.user_award
    award_info = award_detail.award_info
    user = await stp_repo.user.get_user(user_id=user_award.user_id)

    try:
        if action == "approve":
            # Одобряем награду
            await stp_repo.user_award.update_award_status(
                user_award_id=user_award_id,
                status="approved",
                updated_by_user_id=callback.from_user.id,
            )

            await callback.answer(
                f"✅ Награда {award_info.name} для {user.fullname} одобрена!",
                show_alert=True,
            )

            logger.info(
                f"[МИП] - [Одобрение] {callback.from_user.username} ({callback.from_user.id}) одобрил награду {award_info.name} для пользователя {user.username} ({user_award.user_id})"
            )

        elif action == "reject":
            # Отклоняем награду
            await stp_repo.user_award.update_award_status(
                user_award_id=user_award_id,
                status="rejected",
                updated_by_user_id=callback.from_user.id,
            )

            await callback.answer(
                f"⛔ Награда {award_info.name} для {user.fullname} отклонена!",
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


@mip_leveling_router.callback_query(LevelingMenu.filter(F.menu == "achievements_all"))
async def achievements_all(
    callback: CallbackQuery, callback_data: LevelingMenu, stp_repo: RequestsRepo
):
    """
    Обработчик клика на меню всех возможных достижений для МИП
    МИП видит все достижения из всех направлений без фильтрации
    """

    # Достаём номер страницы из callback data, стандартно = 1
    page = getattr(callback_data, "page", 1)

    # Получаем ВСЕ достижения без фильтрации по направлению
    all_achievements = await stp_repo.achievement.get_achievements()

    # Логика пагинации
    achievements_per_page = 5
    total_achievements = len(all_achievements)
    total_pages = (
        total_achievements + achievements_per_page - 1
    ) // achievements_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * achievements_per_page
    end_idx = start_idx + achievements_per_page
    page_achievements = all_achievements[start_idx:end_idx]

    # Построение списка достижений для текущей страницы
    achievements_list = []
    for counter, achievement in enumerate(page_achievements, start=start_idx + 1):
        # Экранируем HTML символы в KPI и других полях
        description = (
            str(achievement.description).replace("<", "&lt;").replace(">", "&gt;")
        )
        name = str(achievement.name).replace("<", "&lt;").replace(">", "&gt;")
        division = str(achievement.division).replace("<", "&lt;").replace(">", "&gt;")
        position = str(achievement.position).replace("<", "&lt;").replace(">", "&gt;")

        achievements_list.append(f"""{counter}. <b>{name}</b>
🏅 Награда: {achievement.reward} баллов
📝 Описание: {description}
🔰 Направление: {division}
👤 Позиция: {position}""")
        achievements_list.append("")

    message_text = f"""<b>🎯 Все возможные достижения</b>
<i>Страница {page} из {total_pages}</i>

<blockquote>Всего достижений:
НТП: {sum(1 for achievement in all_achievements if achievement.division == "НТП")}
НЦК: {sum(1 for achievement in all_achievements if achievement.division == "НЦК")}
Всего: {total_achievements}</blockquote>

{"\n".join(achievements_list)}"""

    logger.info(repr(message_text))
    await callback.message.edit_text(
        message_text, reply_markup=achievements_paginated_kb(page, total_pages)
    )
    logger.info(
        f"[МИП] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыто меню всех достижений, страница {page}"
    )


@mip_leveling_router.callback_query(AwardsMenu.filter(F.menu == "awards_all"))
async def awards_all(
    callback: CallbackQuery, callback_data: AwardsMenu, stp_repo: RequestsRepo
):
    """
    Обработчик клика на меню всех возможных наград для МИП
    МИП видит все награды из всех направлений без фильтрации
    """

    # Достаём номер страницы из callback data, стандартно = 1
    page = getattr(callback_data, "page", 1)

    # Получаем ВСЕ награды без фильтрации по направлению
    all_awards = await stp_repo.award.get_awards()

    # Логика пагинации
    awards_per_page = 5
    total_awards = len(all_awards)
    total_pages = (total_awards + awards_per_page - 1) // awards_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * awards_per_page
    end_idx = start_idx + awards_per_page
    page_awards = all_awards[start_idx:end_idx]

    # Построение списка наград для текущей страницы
    awards_list = []
    for counter, award in enumerate(page_awards, start=start_idx + 1):
        awards_list.append(f"""{counter}. <b>{award.name}</b>
💵 Стоимость: {award.cost} баллов
📝 Описание: {award.description}
🔰 Направление: {award.division}""")
        if award.count > 0:
            awards_list.append(f"""📍 Активаций: {award.count}""")
        awards_list.append("")

    message_text = f"""<b>🏆 Все возможные награды</b>
<i>Страница {page} из {total_pages}</i>

<blockquote expandable>Всего наград:
НТП: {sum(1 for award in all_awards if award.division == "НТП")}
НЦК: {sum(1 for award in all_awards if award.division == "НЦК")}
Всего: {total_awards}</blockquote>

{"\n".join(awards_list)}"""

    await callback.message.edit_text(
        message_text, reply_markup=awards_paginated_kb(page, total_pages)
    )
    logger.info(
        f"[МИП] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыто меню всех наград, страница {page}"
    )
