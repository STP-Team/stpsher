import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from stp_database import Employee
from stp_database.repo.STP.requests import MainRequestsRepo

from tgbot.filters.role import HeadFilter
from tgbot.keyboards.head.group.game.casino import (
    HeadCasinoToggleAll,
    HeadCasinoUserToggle,
    head_casino_management_kb,
)
from tgbot.keyboards.head.group.game.main import HeadGameMenu
from tgbot.keyboards.head.group.members import short_name

head_game_casino_router = Router()
head_game_casino_router.callback_query.filter(
    F.message.chat.type == "private", HeadFilter()
)

logger = logging.getLogger(__name__)


@head_game_casino_router.callback_query(HeadGameMenu.filter(F.menu == "casino"))
async def head_casino_menu(
    callback: CallbackQuery, user: Employee, stp_repo: MainRequestsRepo
):
    """
    Обработчик казино меню для руководителей
    """
    if not user:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\nНе удалось найти информацию в базе данных."
        )
        return

    # Получаем всех сотрудников группы
    group_members = await stp_repo.employee.get_users_by_head(user.fullname)

    if not group_members:
        await callback.message.edit_text(
            """🎲 <b>Казино</b>

У тебя пока нет подчиненных в системе

<i>Если это ошибка, обратись к администратору.</i>""",
            reply_markup=head_casino_management_kb([]),
        )
        return

    # Подсчитываем статистику по казино
    enabled_count = sum(1 for member in group_members if member.is_casino_allowed)
    total_count = len(group_members)

    message_text = f"""🎲 <b>Казино</b>

<b>Статистика группы:</b>
🟢 Разрешено: {enabled_count} человек
🟠 Запрещено: {total_count - enabled_count} человек
👥 Всего в группе: {total_count} человек

<i>Нажми на участника для изменения его доступа</i>"""

    await callback.message.edit_text(
        message_text,
        reply_markup=head_casino_management_kb(group_members),
    )
    logger.info(
        f"[Руководитель] - [Казино] {callback.from_user.username} ({callback.from_user.id}): Открыто меню управления казино"
    )


@head_game_casino_router.callback_query(HeadCasinoUserToggle.filter())
async def toggle_user_casino_access(
    callback: CallbackQuery,
    callback_data: HeadCasinoUserToggle,
    user: Employee,
    stp_repo: MainRequestsRepo,
):
    """
    Обработчик переключения доступа к казино для пользователя
    """
    if not user:
        await callback.answer("❌ Ошибка получения данных", show_alert=True)
        return

    member = await stp_repo.employee.get_user(main_id=callback_data.user_id)

    if not member:
        await callback.answer("❌ Участник не найден", show_alert=True)
        return

    # Проверяем, что участник в группе руководителя
    group_members = await stp_repo.employee.get_users_by_head(user.fullname)
    if not any(m.id == member.id for m in group_members):
        await callback.answer("❌ Участник не в вашей группе", show_alert=True)
        return

    # Переключаем статус доступа к казино
    new_status = not member.is_casino_allowed
    await stp_repo.employee.update_user(
        user_id=member.user_id, is_casino_allowed=new_status
    )

    status_text = "разрешен" if new_status else "запрещен"
    emoji_status = "🟢" if new_status else "🟠"

    # Обновляем сообщение
    await head_casino_menu(callback, user, stp_repo)

    # Показываем уведомление
    await callback.answer(
        f"{emoji_status} {short_name(member.fullname)}: доступ к казино {status_text}"
    )

    logger.info(
        f"[Руководитель] - [Казино] {callback.from_user.username} ({callback.from_user.id}): Изменен доступ к казино для {member.fullname}: {status_text}"
    )


@head_game_casino_router.callback_query(HeadCasinoToggleAll.filter())
async def toggle_all_casino_access(
    callback: CallbackQuery,
    callback_data: HeadCasinoToggleAll,
    user: Employee,
    stp_repo: MainRequestsRepo,
):
    """
    Обработчик массового переключения доступа к казино для всех пользователей группы
    """
    if not user:
        await callback.answer("❌ Ошибка получения данных", show_alert=True)
        return

    # Получаем всех сотрудников группы
    group_members = await stp_repo.employee.get_users_by_head(user.fullname)

    if not group_members:
        await callback.answer("❌ Участники не найдены", show_alert=True)
        return

    action = callback_data.action
    changes_count = 0

    for member in group_members:
        if not member.user_id:  # Пропускаем неавторизованных
            continue

        new_status = None
        if action == "enable_all":
            if not member.is_casino_allowed:
                new_status = True
        elif action == "disable_all":
            if member.is_casino_allowed:
                new_status = False
        elif action == "toggle_all":
            new_status = not member.is_casino_allowed

        if new_status is not None:
            await stp_repo.employee.update_user(
                user_id=member.user_id, is_casino_allowed=new_status
            )
            changes_count += 1

    # Обновляем сообщение
    await head_casino_menu(callback, user, stp_repo)

    # Показываем уведомление
    if action == "enable_all":
        action_text = "разрешен"
        emoji = "🟢"
    elif action == "disable_all":
        action_text = "запрещен"
        emoji = "🟠"
    else:
        action_text = "изменен"
        emoji = "🔄"

    await callback.answer(
        f"{emoji} Доступ к казино {action_text} для {changes_count} участников"
    )

    logger.info(
        f"[Руководитель] - [Казино] {callback.from_user.username} ({callback.from_user.id}): Массово изменен доступ к казино для {changes_count} участников ({action})"
    )
