from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class GroupSettingsMenu(CallbackData, prefix="group"):
    group_id: int
    menu: str


def group_settings_keyboard(group_id: int) -> InlineKeyboardMarkup:
    """Create keyboard for group settings."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Удалять уволенных",
                    callback_data=GroupSettingsMenu(
                        group_id=group_id, menu="remove_fired"
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Закрыть",
                    callback_data=GroupSettingsMenu(
                        group_id=group_id, menu="close"
                    ).pack(),
                )
            ],
        ]
    )
