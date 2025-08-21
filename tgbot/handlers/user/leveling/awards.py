import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.keyboards.mip.leveling.main import LevelingMenu
from tgbot.keyboards.user.leveling.main import (
    AwardDetailMenu,
    AwardHistoryMenu,
    AwardsMenu,
    award_detail_back_kb,
    award_history_kb,
    awards_kb,
    awards_paginated_kb,
    get_status_emoji,
)

user_leveling_awards_router = Router()
user_leveling_awards_router.message.filter(
    F.chat.type == "private",
)
user_leveling_awards_router.callback_query.filter(F.message.chat.type == "private")

logger = logging.getLogger(__name__)


@user_leveling_awards_router.callback_query(LevelingMenu.filter(F.menu == "awards"))
async def user_awards_cb(callback: CallbackQuery, stp_repo: RequestsRepo):
    await callback.message.edit_text(
        """<b>👏 Награды</b>

Здесь ты можешь найти доступные для приобретения, а так же все возможные награды

<i>Используй меню для выбора действия</i>""",
        reply_markup=awards_kb(),
    )


@user_leveling_awards_router.callback_query(AwardsMenu.filter(F.menu == "all"))
async def awards_all(
    callback: CallbackQuery,
    user: User,
    callback_data: AwardsMenu,
    stp_repo: RequestsRepo,
):
    """
    Обработчик клика на меню всех возможных наград
    """

    # Достаём номер страницы из callback data, стандартно = 1
    page = getattr(callback_data, "page", 1)

    all_awards = await stp_repo.award.get_awards(
        division="НТП" if "НТП" in user.division else "НЦК"
    )

    # Логика пагинации
    awards_per_page = 5
    total_awards = len(all_awards)
    total_pages = (total_awards + awards_per_page - 1) // awards_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * awards_per_page  # Используем переменную page
    end_idx = start_idx + awards_per_page
    page_awards = all_awards[start_idx:end_idx]

    # Построение списка наград для текущей страницы
    awards_list = []
    for counter, award in enumerate(page_awards, start=start_idx + 1):
        awards_list.append(f"""{counter}. <b>{award.name}</b>
💵 Стоимость: {award.cost}
📝 Описание: {award.description}""")
        if award.count > 0:
            awards_list.append(f"""🧮 Активаций: {award.count}""")
        awards_list.append("")

    message_text = f"""<b>🏆 Все возможные награды</b>
<i>Страница {page} из {total_pages}</i>

{"\n".join(awards_list)}"""

    await callback.message.edit_text(
        message_text, reply_markup=awards_paginated_kb(page, total_pages)
    )
    logger.info(
        f"[Пользователь] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыто меню всех наград, страница {page}"
    )


@user_leveling_awards_router.callback_query(AwardsMenu.filter(F.menu == "executed"))
async def awards_history(callback: CallbackQuery, stp_repo: RequestsRepo):
    """Показывает историю наград пользователя в виде клавиатуры с пагинацией"""
    user_awards_with_details = await stp_repo.user_award.get_user_awards_with_details(
        user_id=callback.from_user.id
    )

    if not user_awards_with_details:
        await callback.message.edit_text(
            """<b>✴️ Использованные награды</b>

Здесь ты найдешь все приобретенные награды, а так же их статус и многое другое

У тебя пока нет использованных наград 🙂

<i>Используй меню для возврата</i>""",
            reply_markup=award_detail_back_kb(),
        )
        return

    # Показываем первую страницу по умолчанию
    total_awards = len(user_awards_with_details)
    message_text = f"""<b>✴️ Использованные награды</b>

Здесь ты найдешь все приобретенные награды, а так же их статус и многое другое

<i>Всего наград: {total_awards}</i>
<i>Используй меню для просмотра награды</i>"""

    await callback.message.edit_text(
        message_text,
        reply_markup=award_history_kb(user_awards_with_details, current_page=1),
    )


@user_leveling_awards_router.callback_query(AwardHistoryMenu.filter())
async def awards_history_pagination(
    callback: CallbackQuery, callback_data: AwardHistoryMenu, stp_repo: RequestsRepo
):
    """Обработчик пагинации истории наград"""
    page = callback_data.page

    user_awards_with_details = await stp_repo.user_award.get_user_awards_with_details(
        user_id=callback.from_user.id
    )

    if not user_awards_with_details:
        await callback.message.edit_text(
            """<b>✴️ Использованные награды</b>

У тебя пока нет использованных наград 🙂

<i>Используй меню для возврата</i>""",
            reply_markup=award_detail_back_kb(),
        )
        return

    total_awards = len(user_awards_with_details)
    message_text = f"""<b>✴️ Использованные награды</b>

Здесь ты найдешь все приобретенные награды, а так же их статус и многое другое

<i>Всего наград: {total_awards}</i>
<i>Используй меню для просмотра награды</i>"""

    await callback.message.edit_text(
        message_text,
        reply_markup=award_history_kb(user_awards_with_details, current_page=page),
    )


@user_leveling_awards_router.callback_query(AwardDetailMenu.filter())
async def award_detail_view(
    callback: CallbackQuery, callback_data: AwardDetailMenu, stp_repo: RequestsRepo
):
    """Показывает детальную информацию о конкретной награде"""
    user_award_id = callback_data.user_award_id

    # Получаем информацию о конкретной награде
    user_award_detail = await stp_repo.user_award.get_user_award_detail(user_award_id)

    if not user_award_detail:
        await callback.message.edit_text(
            """<b>🏆 Просмотр награды</b>

Не смог найти описание для награды ☹""",
            reply_markup=award_detail_back_kb(),
        )
        return

    user_award = user_award_detail.user_award
    award_info = user_award_detail.award_info

    # Получаем эмодзи и название статуса
    status_emoji = get_status_emoji(user_award.status)
    status_names = {
        "waiting": "Ожидает подтверждения",
        "approved": "Одобрена",
        "canceled": "Отменена",
        "rejected": "Отклонена",
    }
    status_name = status_names.get(user_award.status, "Неизвестный статус")

    # Форматируем информацию об активациях
    usage_info = f"🧮 Использований: {user_award_detail.current_usages} из {user_award_detail.max_usages}"

    # Формируем сообщение с подробной информацией
    message_text = f"""<b>🏆 Просмотр награды - {award_info.name}</b>

<b>📊 Статус:</b> {status_emoji} {status_name}
<b>💵 Стоимость:</b> {award_info.cost} баллов
<b>📝 Описание:</b> {award_info.description}
{usage_info}

<b>📅 Дата покупки:</b> {user_award.bought_at.strftime("%d.%m.%Y в %H:%M")}"""

    if user_award.comment:
        message_text += f"\n\n<b>💬 Комментарий:</b> {user_award.comment}"

    if user_award.approved_by_user_id:
        message_text += f"\n<b>👤 Одобрил:</b> ID {user_award.approved_by_user_id}"
        message_text += f"\n<b>📅 Дата одобрения:</b> {user_award.approved_at.strftime('%d.%m.%Y в %H:%M')}"

    await callback.message.edit_text(message_text, reply_markup=award_detail_back_kb())
