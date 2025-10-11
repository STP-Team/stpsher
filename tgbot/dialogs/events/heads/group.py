"""Обработчики для управления группой руководителя."""

import logging

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, ManagedCheckbox, Select
from stp_database import MainRequestsRepo

from tgbot.dialogs.states.heads.group import HeadGroupSG
from tgbot.misc.dicts import roles

logger = logging.getLogger(__name__)


async def start_group_dialog(
    _callback: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик перехода в диалог групп.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(
        HeadGroupSG.menu,
    )


async def close_group_dialog(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик возврата к главному диалогу из диалога групп.

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.done()


async def on_member_select(
    _callback: CallbackQuery, _widget: Select, dialog_manager, item_id, **_kwargs
) -> None:
    """Обработчик выбора члена группы из списка.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранного пользователя
    """
    dialog_manager.dialog_data["selected_member_id"] = item_id

    # Получаем информацию о пользователе и устанавливаем состояние чекбокса казино
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")
    searched_user = await stp_repo.employee.get_users(main_id=int(item_id))

    casino_checkbox: ManagedCheckbox = dialog_manager.find("member_casino_access")
    if casino_checkbox:
        await casino_checkbox.set_checked(searched_user.is_casino_allowed)

    await dialog_manager.switch_to(HeadGroupSG.member_details)


async def on_member_casino_change(
    callback: CallbackQuery, widget: ManagedCheckbox, dialog_manager: DialogManager
):
    """Обработчик изменения доступа к казино для члена группы.

    Args:
        callback: Callback query от Telegram
        widget: Управляемый чекбокс
        dialog_manager: Менеджер диалога
    """
    try:
        stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")
        selected_member_id = dialog_manager.dialog_data.get("selected_member_id")

        if not stp_repo or not selected_member_id:
            await callback.answer("❌ Ошибка: пользователь не выбран", show_alert=True)
            return

        # Получаем текущее состояние чекбокса
        is_casino_allowed = widget.is_checked()

        # Получаем пользователя
        searched_user = await stp_repo.employee.get_users(
            main_id=int(selected_member_id)
        )
        if not searched_user:
            searched_user = await stp_repo.employee.get_users(
                user_id=int(selected_member_id)
            )

        if not searched_user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Проверяем, действительно ли состояние изменилось
        if searched_user.is_casino_allowed == is_casino_allowed:
            return

        # Обновляем доступ к казино в базе данных
        await stp_repo.employee.update_user(
            user_id=searched_user.user_id, is_casino_allowed=is_casino_allowed
        )

        # Показываем уведомление
        status_text = "включен" if is_casino_allowed else "выключен"
        await callback.answer(f"✅ Доступ к казино {status_text}")

    except Exception as e:
        logger.error(f"[Казино] Ошибка при изменении доступа: {e}")
        await callback.answer("❌ Ошибка при изменении доступа", show_alert=True)


async def on_member_role_change(
    callback: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
    **_kwargs,
) -> None:
    """Обработчик изменения роли члена группы.

    Args:
        callback: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        item_id: ID выбранной роли
    """
    try:
        stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")
        selected_member_id = dialog_manager.dialog_data.get("selected_member_id")

        if not stp_repo or not selected_member_id:
            await callback.answer("❌ Ошибка: пользователь не выбран", show_alert=True)
            return

        new_role_id = int(item_id)
        role_info = roles.get(new_role_id)

        if not role_info:
            await callback.answer("❌ Ошибка: роль не найдена", show_alert=True)
            return

        # Обновляем роль пользователя
        searched_user = await stp_repo.employee.get_users(
            main_id=int(selected_member_id)
        )
        if not searched_user:
            searched_user = await stp_repo.employee.get_users(
                user_id=int(selected_member_id)
            )

        if not searched_user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Обновляем роль в базе данных
        await stp_repo.employee.update_user(
            user_id=searched_user.user_id, role=new_role_id
        )

        # Показываем уведомление о смене роли
        await callback.answer(
            f"✅ Роль изменена на: {role_info['emoji']} {role_info['name']}"
        )

        # Возвращаемся к деталям пользователя
        await dialog_manager.switch_to(HeadGroupSG.member_details)

    except Exception as e:
        logger.error(f"[Смена роли] Ошибка при изменении роли: {e}")
        await callback.answer("❌ Ошибка при изменении роли", show_alert=True)


async def on_member_schedule_mode_select(
    _callback: CallbackQuery,
    _widget,
    dialog_manager: DialogManager,
    item_id: str,
    **_kwargs,
) -> None:
    """Изменение режима отображения графика члена группы.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные от виджета
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранного режима
    """
    dialog_manager.dialog_data["schedule_mode"] = item_id
    await dialog_manager.switch_to(HeadGroupSG.member_schedule)
