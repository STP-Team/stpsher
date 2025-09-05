from aiogram import F, Router
from aiogram.types import CallbackQuery

from tgbot.filters.role import HeadFilter
from tgbot.keyboards.head.group.main import GroupManagementMenu, group_management_kb
from tgbot.keyboards.user.main import MainMenu

head_group_router = Router()
head_group_router.message.filter(F.chat.type == "private", HeadFilter())
head_group_router.callback_query.filter(F.message.chat.type == "private", HeadFilter())


@head_group_router.callback_query(MainMenu.filter(F.menu == "group_management"))
async def group_management_cb(callback: CallbackQuery):
    """Обработчик управления группой"""
    await callback.message.edit_text(
        """👥 <b>Управление группой</b>

Используй меню для выбора действия""",
        reply_markup=group_management_kb(),
    )


@head_group_router.callback_query(GroupManagementMenu.filter(F.menu == "kpi"))
async def group_mgmt_kpi_members_cb(callback: CallbackQuery):
    """Обработчик KPI участников группы"""
    await callback.message.edit_text(
        """📊 <b>KPI группы</b>

<i>Функция в разработке</i>

Здесь будут отображены индивидуальные показатели каждого участника вашей группы с возможностью детального анализа.""",
        reply_markup=group_management_kb(),
    )


@head_group_router.callback_query(GroupManagementMenu.filter(F.menu == "game"))
async def group_mgmt_game_cb(callback: CallbackQuery):
    """Обработчик игровых возможностей группы"""
    await callback.message.edit_text(
        """🏮 <b>Игра</b>

<i>Функция в разработке</i>"""
    )
