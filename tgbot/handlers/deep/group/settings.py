import logging

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, ChatMember, Message
from aiogram.utils.payload import decode_payload

from infrastructure.database.models.STP.group import Group
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.deep import DeepLinkRegexFilter
from tgbot.keyboards.group.settings import (
    GroupAccessApplyMenu,
    GroupAccessMenu,
    GroupSettingsMenu,
    group_access_keyboard,
    group_settings_keyboard,
)

deeplink_group = Router()
logger = logging.getLogger(__name__)

# Store pending role changes per group
pending_role_changes = {}


@deeplink_group.message(
    CommandStart(deep_link=True), DeepLinkRegexFilter(r"^group_-?\d+$")
)
async def handle_settings(
    message: Message, command: CommandObject, stp_repo: MainRequestsRepo
):
    payload = decode_payload(command.args)
    group_id = payload.split("_", 1)[1]

    member: ChatMember = await message.bot.get_chat_member(
        chat_id=group_id, user_id=message.from_user.id
    )

    if member.status in ["administrator", "creator"]:
        group = await stp_repo.group.get_group(int(group_id))
        group_info = await message.bot.get_chat(chat_id=group.group_id)

        await message.answer(
            f"""⚙️ <b>Настройки группы</b>: {group_info.full_name}

<b>Обозначения</b>
- 🟢 Опция включена
- 🟠 Опция выключена

Часть опций содержит в себе детальные настройки, открыть их можно нажав на название опции

<i>Используй меню для управления функциями бота в группе</i>""",
            reply_markup=group_settings_keyboard(group),
        )
    else:
        await message.answer(
            "Доступ к настройкам группы есть только у администраторов этой группы"
        )


async def _update_toggle_setting(
    callback: CallbackQuery,
    stp_repo: MainRequestsRepo,
    group: Group,
    field_name: str,
    current_value: bool,
    success_message: str,
) -> None:
    """Helper function to update toggle settings efficiently."""
    new_value = not current_value
    update_data = {field_name: new_value}

    logger.info(
        f"Updating group {group.group_id}: {field_name} from {current_value} to {new_value}"
    )

    updated_group = await stp_repo.group.update_group(
        group_id=group.group_id, **update_data
    )

    if updated_group:
        status = "включено" if new_value else "выключено"
        await callback.answer(f"{success_message} {status}")

        await callback.message.edit_reply_markup(
            reply_markup=group_settings_keyboard(updated_group)
        )
        logger.info(f"Successfully updated group {group.group_id} setting {field_name}")
    else:
        await callback.answer("Ошибка при обновлении настройки")
        logger.error(f"Failed to update group {group.group_id} setting {field_name}")


@deeplink_group.callback_query(GroupSettingsMenu.filter())
async def handle_settings_callback(
    callback: CallbackQuery,
    callback_data: GroupSettingsMenu,
    stp_repo: MainRequestsRepo,
):
    group = await stp_repo.group.get_group(callback_data.group_id)
    if not group:
        await callback.answer("Не удалось найти группу в базе :(")
        return

    match callback_data.menu:
        case "remove_unemployed":
            await _update_toggle_setting(
                callback,
                stp_repo,
                group,
                "remove_unemployed",
                group.remove_unemployed,
                "Проверка регистрации",
            )

        case "is_casino_allowed":
            await _update_toggle_setting(
                callback,
                stp_repo,
                group,
                "is_casino_allowed",
                group.is_casino_allowed,
                "Казино",
            )

        case "new_user_notify":
            await _update_toggle_setting(
                callback,
                stp_repo,
                group,
                "new_user_notify",
                group.new_user_notify,
                "Приветствие новых участников",
            )

        case "access":
            # Initialize pending changes with current roles
            pending_role_changes[group.group_id] = (group.allowed_roles or []).copy()

            await callback.message.edit_text(
                """🛡️ <b>Уровень доступа к группе</b>

<b>Обозначения</b>
- 🟢 Имеет доступ
- 🔴 Не имеет доступа

<i>Выбери роли, которые должны иметь доступ к группе, затем нажми "Применить"</i>
<i>Если выключить все роли - у любого сотрудника будет доступ</i>""",
                reply_markup=group_access_keyboard(
                    group, pending_role_changes[group.group_id]
                ),
            )

        case "members":
            await callback.answer("Управление составом группы")
            # TODO: Implement members management submenu

        case "back":
            group_info = await callback.bot.get_chat(chat_id=group.group_id)
            await callback.message.edit_text(
                f"""⚙️ <b>Настройки группы</b>: {group_info.full_name}

<b>Обозначения</b>
- 🟢 Опция включена
- 🟠 Опция выключена

Часть опций содержит в себе детальные настройки, открыть их можно нажав на название опции

<i>Используй меню для управления функциями бота в группе</i>""",
                reply_markup=group_settings_keyboard(group),
            )


@deeplink_group.callback_query(GroupAccessMenu.filter())
async def handle_access_callback(
    callback: CallbackQuery,
    callback_data: GroupAccessMenu,
    stp_repo: MainRequestsRepo,
):
    group = await stp_repo.group.get_group(callback_data.group_id)
    if not group:
        await callback.answer("Не удалось найти группу в базе :(")
        return

    # Get current pending roles for this group
    if group.group_id not in pending_role_changes:
        pending_role_changes[group.group_id] = (group.allowed_roles or []).copy()

    current_pending = pending_role_changes[group.group_id]
    role_id = callback_data.role_id

    if role_id in current_pending:
        # Remove role from pending list
        pending_role_changes[group.group_id] = [
            r for r in current_pending if r != role_id
        ]
        action = "убрана из выбранных"
    else:
        # Add role to pending list
        pending_role_changes[group.group_id] = current_pending + [role_id]
        action = "добавлена к выбранным"

    from tgbot.misc.dicts import roles

    role_name = roles[role_id]["name"]
    await callback.answer(f"Роль '{role_name}' {action}")

    # Update keyboard with pending changes
    await callback.message.edit_reply_markup(
        reply_markup=group_access_keyboard(group, pending_role_changes[group.group_id])
    )


@deeplink_group.callback_query(GroupAccessApplyMenu.filter())
async def handle_access_apply_callback(
    callback: CallbackQuery,
    callback_data: GroupAccessApplyMenu,
    stp_repo: MainRequestsRepo,
):
    group = await stp_repo.group.get_group(callback_data.group_id)
    if not group:
        await callback.answer("Не удалось найти группу в базе :(")
        return

    if callback_data.action == "apply":
        # Apply the pending changes
        if group.group_id in pending_role_changes:
            new_roles = pending_role_changes[group.group_id]

            updated_group = await stp_repo.group.update_group(
                group_id=group.group_id, allowed_roles=new_roles
            )

            if updated_group:
                await callback.answer("✅ Настройки доступа применены!")

                # Clean up pending changes
                del pending_role_changes[group.group_id]

                # Update keyboard without pending changes
                await callback.message.edit_reply_markup(
                    reply_markup=group_access_keyboard(updated_group)
                )
                logger.info(
                    f"Successfully applied access roles for group {group.group_id}"
                )
            else:
                await callback.answer("❌ Ошибка при применении настроек")
                logger.error(f"Failed to apply access roles for group {group.group_id}")
        else:
            await callback.answer("Нет изменений для применения")

    elif callback_data.action == "cancel":
        # Cancel pending changes
        if group.group_id in pending_role_changes:
            del pending_role_changes[group.group_id]

        await callback.answer("❌ Изменения отменены")

        # Update keyboard with original roles
        await callback.message.edit_reply_markup(
            reply_markup=group_access_keyboard(group)
        )
