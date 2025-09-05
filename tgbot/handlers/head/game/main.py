import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import HeadFilter
from tgbot.keyboards.head.group.game.main import head_game_kb
from tgbot.keyboards.head.group.main import GroupManagementMenu
from tgbot.keyboards.head.group.members import short_name

head_game_router = Router()
head_game_router.callback_query.filter(F.message.chat.type == "private", HeadFilter())

logger = logging.getLogger(__name__)


@head_game_router.callback_query(GroupManagementMenu.filter(F.menu == "game"))
async def head_game_menu(callback: CallbackQuery, stp_repo: MainRequestsRepo):
    """
    Обработчик игрового меню для руководителей
    """
    current_user = await stp_repo.employee.get_user(user_id=callback.from_user.id)

    if not current_user:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\nНе удалось найти вашу информацию в базе данных."
        )
        return

    # Получаем статистику группы
    group_stats = await stp_repo.transaction.get_group_stats_by_head(
        current_user.fullname
    )

    # Получаем ТОП-3 за все время
    all_time_top_3 = await stp_repo.transaction.get_group_all_time_top_3(
        current_user.fullname
    )

    # Формируем текст с информацией о группе
    months_ru = {
        1: "январь",
        2: "февраль",
        3: "март",
        4: "апрель",
        5: "май",
        6: "июнь",
        7: "июль",
        8: "август",
        9: "сентябрь",
        10: "октябрь",
        11: "ноябрь",
        12: "декабрь",
    }
    current_month_name = f"{months_ru[datetime.now().month]} {datetime.now().year}"

    stats_text = f"""📊 <b>Статистика группы</b>

💎 <b>Общие баллы группы:</b> {group_stats["total_points"]} баллов
⚡ <b>Средний уровень группы:</b> {group_stats["group_level"]}

🏆 <b>ТОП-3 за {current_month_name}:</b>"""

    if group_stats["top_3_this_month"]:
        position_emojis = ["🥇", "🥈", "🥉"]
        for i, user_stat in enumerate(group_stats["top_3_this_month"]):
            stats_text += f"\n{position_emojis[i]} <a href='t.me/{user_stat['username']}'>{short_name(user_stat['name'])}</a> - {user_stat['points']} баллов"
    else:
        stats_text += "\n<i>В этом месяце еще нет активности</i>"

    stats_text += "\n\n🌟 <b>ТОП-3 за все время:</b>"

    if all_time_top_3:
        position_emojis = ["🥇", "🥈", "🥉"]
        for i, user_stat in enumerate(all_time_top_3):
            stats_text += f"\n{position_emojis[i]} <a href='t.me/{user_stat['username']}'>{short_name(user_stat['name'])}</a> - {user_stat['points']} баллов"
    else:
        stats_text += "\n<i>Пока нет данных</i>"

    await callback.message.edit_text(
        stats_text, reply_markup=head_game_kb(), parse_mode="HTML"
    )
    logger.info(
        f"[Руководитель] - [Игровые достижения] {callback.from_user.username} ({callback.from_user.id}): Открыто меню игровых достижений группы"
    )
