from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import Employee
from tgbot.filters.role import HeadFilter
from tgbot.handlers.user.schedule.main import schedule_service
from tgbot.keyboards.head.group import group_management_kb, GroupManagementMenu
from tgbot.keyboards.head.schedule.main import schedule_kb_head
from tgbot.keyboards.user.schedule.main import get_yekaterinburg_date, group_schedule_kb
from tgbot.handlers.head.schedule.group import head_group_schedule_service
from tgbot.keyboards.user.main import MainMenu

head_group_router = Router()
head_group_router.message.filter(F.chat.type == "private", HeadFilter())
head_group_router.callback_query.filter(F.message.chat.type == "private", HeadFilter())


@head_group_router.callback_query(MainMenu.filter(F.menu == "group_management"))
async def group_management_cb(callback: CallbackQuery):
    """Обработчик управления группой"""
    await callback.message.edit_text(
        """👥 <b>Управление группой</b>

Выберите действие для управления вашей группой:""",
        reply_markup=group_management_kb(),
    )


@head_group_router.callback_query(GroupManagementMenu.filter(F.menu == "schedule"))
async def group_mgmt_schedule_cb(callback: CallbackQuery, user: Employee, stp_repo):
    """Обработчик расписания группы из меню управления"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    try:
        current_date = get_yekaterinburg_date()

        # Получаем групповое расписание для руководителя
        (
            text,
            total_pages,
            has_prev,
            has_next,
        ) = await head_group_schedule_service.get_group_schedule_for_head(
            user, current_date, 1, stp_repo
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=group_schedule_kb(
                current_date=current_date,
                page=1,
                total_pages=total_pages,
                has_prev=has_prev,
                has_next=has_next,
                user_type="head",
                from_group_mgmt=True,
            ),
        )

    except Exception as e:
        await schedule_service.handle_schedule_error(callback, e)


@head_group_router.callback_query(GroupManagementMenu.filter(F.menu == "kpi_members"))
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


@head_group_router.callback_query(GroupManagementMenu.filter(F.menu == "members"))
async def group_mgmt_members_cb(callback: CallbackQuery):
    """Обработчик состава группы"""
    await callback.message.edit_text(
        """👥 <b>Состав группы</b>

<i>Функция в разработке</i>

Здесь будет отображен полный состав вашей группы с контактной информацией, ролями и статусами участников.""",
        reply_markup=group_management_kb(),
    )
