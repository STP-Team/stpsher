"""Кастомные виджеты для диалогов."""

from aiogram_dialog.widgets.kbd import Url
from aiogram_dialog.widgets.text import Const

SUPPORT_BTN = Url(Const("🛟 Помогите"), url=Const("t.me/stp_helpbot"))
