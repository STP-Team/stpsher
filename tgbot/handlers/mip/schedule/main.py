import datetime
import logging
from typing import Optional

import pytz
from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from tgbot.keyboards.user.main import MainMenu, auth_kb
from tgbot.keyboards.user.schedule.main import (
    DutyNavigation,
    HeadNavigation,
    MonthNavigation,
    ScheduleMenu,
    create_detailed_schedule_keyboard,
    duties_kb,
    get_yekaterinburg_date,
    heads_kb,
    schedule_kb,
    schedule_with_month_kb,
)
from tgbot.misc.dicts import russian_months
from tgbot.services.schedule import (
    DutyScheduleParser,
    HeadScheduleParser,
    ScheduleError,
    ScheduleFileNotFoundError,
    ScheduleParser,
    ScheduleType,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)

user_schedule_router = Router()
user_schedule_router.message.filter(F.chat.type == "private")
user_schedule_router.callback_query.filter(F.message.chat.type == "private")


class ScheduleHandlerService:
    """Сервис для обработки операций с расписанием"""

    def __init__(self):
        self.schedule_parser = ScheduleParser()
        self.duty_parser = DutyScheduleParser()
        self.head_parser = HeadScheduleParser()
        self.yekaterinburg_tz = pytz.timezone("Asia/Yekaterinburg")

    async def check_user_auth(self, callback: CallbackQuery, user: User) -> bool:
        """Проверяет авторизацию пользователя"""
        if not user:
            await callback.message.answer(
                """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
                reply_markup=auth_kb(),
            )
            return False
        return True

    async def handle_schedule_error(
        self, callback: CallbackQuery, error: Exception, fallback_markup=None
    ) -> None:
        """Обработка ошибок расписания"""
        if fallback_markup is None:
            fallback_markup = schedule_kb()

        if isinstance(error, UserNotFoundError):
            error_msg = "❌ Пользователь не найден в расписании"
        elif isinstance(error, ScheduleFileNotFoundError):
            error_msg = "❌ Файл расписания не найден"
        elif isinstance(error, ScheduleError):
            error_msg = f"❌ Ошибка расписания: {error}"
        else:
            error_msg = f"❌ Ошибка при получении данных:\n<code>{error}</code>"

        logger.error(f"Schedule error: {error}", exc_info=True)

        try:
            await callback.message.edit_text(
                text=error_msg,
                reply_markup=fallback_markup,
            )
        except Exception as edit_error:
            logger.error(f"Failed to edit message: {edit_error}")
            await callback.answer(error_msg, show_alert=True)

    def get_current_month(self) -> str:
        """Получает текущий месяц"""
        return russian_months[datetime.datetime.now().month]

    def parse_date_from_callback(self, date_str: str) -> datetime.datetime:
        """Парсит дату из callback data"""
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return self.yekaterinburg_tz.localize(target_date)

    async def get_user_schedule_response(
        self, user: User, month: str, compact: bool = True
    ) -> str:
        """Получает расписание пользователя"""
        return self.schedule_parser.get_user_schedule_formatted(
            fullname=user.fullname,
            month=month,
            division=user.division,
            compact=compact,
            schedule_type=ScheduleType.REGULAR,
        )

    async def get_duties_response(
        self, division: str, date: Optional[datetime.datetime] = None, stp_repo=None
    ) -> str:
        """Получает расписание дежурных"""
        if date is None:
            date = get_yekaterinburg_date()

        duties = self.duty_parser.get_duties_for_date(date, division)

        # Filter out duties who are not in the database (fired employees)
        if stp_repo:
            active_duties = []
            for duty in duties:
                try:
                    user = await stp_repo.users.get_user(fullname=duty.name)
                    if user:
                        active_duties.append(duty)
                    else:
                        logger.debug(
                            f"[График дежурств] Сотрудник {duty.name} не найден в базе данных"
                        )
                except Exception as e:
                    logger.debug(
                        f"[График дежурств] Ошибка проверки сотрудника {duty.name} в БД: {e}"
                    )
                    # If we can't check, include the duty to avoid false negatives
                    active_duties.append(duty)
            duties = active_duties

        return self.duty_parser.format_duties_for_date(date, duties)

    async def get_heads_response(
        self, division: str, date: Optional[datetime.datetime] = None, stp_repo=None
    ) -> str:
        """Получает расписание руководителей групп"""
        if date is None:
            date = get_yekaterinburg_date()

        heads = await self.head_parser.get_heads_for_date(date, division, stp_repo)

        # Filter out heads who are not in the database (fired employees)
        if stp_repo:
            active_heads = []
            for head in heads:
                try:
                    user = await stp_repo.users.get_user(fullname=head.name)
                    if user:
                        active_heads.append(head)
                    else:
                        logger.debug(
                            f"[График РГ] Сотрудник {head.name} не найден в базе данных"
                        )
                except Exception as e:
                    logger.debug(
                        f"[График РГ] Ошибка проверки сотрудника {head.name} в БД: {e}"
                    )
                    # If we can't check, include the head to avoid false negatives
                    active_heads.append(head)
            heads = active_heads

        return self.head_parser.format_heads_for_date(date, heads)


# Создаем единственный экземпляр сервиса
schedule_service = ScheduleHandlerService()


@user_schedule_router.callback_query(MainMenu.filter(F.menu == "schedule"))
async def schedule(callback: CallbackQuery, user: User):
    """Главное меню расписаний"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    await callback.message.edit_text(
        """📅 Меню графиков

Используй меню для выбора действия""",
        reply_markup=schedule_kb(),
    )


@user_schedule_router.callback_query(ScheduleMenu.filter(F.menu == "my"))
async def user_schedule(callback: CallbackQuery, user: User):
    """Обработчик личного расписания"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    try:
        month = schedule_service.get_current_month()
        schedule_text = await schedule_service.get_user_schedule_response(
            user=user, month=month, compact=True
        )

        await callback.message.edit_text(
            text=schedule_text,
            reply_markup=schedule_with_month_kb(
                current_month=month, schedule_type="my"
            ),
        )

    except Exception as e:
        await schedule_service.handle_schedule_error(callback, e)


@user_schedule_router.callback_query(MonthNavigation.filter(F.action == "compact"))
async def handle_compact_view(callback: CallbackQuery, user: User):
    """Обработчик перехода к компактному виду"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    callback_data = MonthNavigation.unpack(callback.data)
    current_month = callback_data.current_month
    schedule_type = callback_data.schedule_type

    try:
        schedule_text = await schedule_service.get_user_schedule_response(
            user=user, month=current_month, compact=True
        )

        await callback.message.edit_text(
            text=schedule_text,
            reply_markup=schedule_with_month_kb(
                current_month=current_month, schedule_type=schedule_type
            ),
        )
        await callback.answer()

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@user_schedule_router.callback_query(MonthNavigation.filter())
async def handle_month_navigation(
    callback: CallbackQuery, callback_data: MonthNavigation, user: User
):
    """Обработчик навигации по месяцам"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    action = callback_data.action
    current_month = callback_data.current_month
    schedule_type = callback_data.schedule_type

    try:
        if action in ["prev", "next"]:
            # Компактный режим для навигации
            schedule_text = await schedule_service.get_user_schedule_response(
                user=user, month=current_month, compact=True
            )

            await callback.message.edit_text(
                text=schedule_text,
                reply_markup=schedule_with_month_kb(
                    current_month=current_month, schedule_type=schedule_type
                ),
            )

        elif action == "detailed":
            # Детальный режим
            schedule_text = await schedule_service.get_user_schedule_response(
                user=user, month=current_month, compact=False
            )

            keyboard = create_detailed_schedule_keyboard(current_month, schedule_type)
            await callback.message.edit_text(
                text=schedule_text,
                reply_markup=keyboard,
            )

        await callback.answer()

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@user_schedule_router.callback_query(ScheduleMenu.filter(F.menu == "duties"))
async def duties_schedule(callback: CallbackQuery, user: User, stp_repo):
    """Обработчик расписания дежурных"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    try:
        current_date = get_yekaterinburg_date()
        duties_text = await schedule_service.get_duties_response(
            division=user.division, date=current_date, stp_repo=stp_repo
        )

        await callback.message.edit_text(
            text=duties_text,
            reply_markup=duties_kb(current_date),
        )

    except Exception as e:
        await schedule_service.handle_schedule_error(callback, e)


@user_schedule_router.callback_query(DutyNavigation.filter())
async def handle_duty_navigation(
    callback: CallbackQuery, callback_data: DutyNavigation, user: User, stp_repo
):
    """Обработчик навигации по дежурствам"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    try:
        action = callback_data.action

        if action == "-":
            await callback.answer()
            return

        # Определяем целевую дату
        if action == "today":
            target_date = get_yekaterinburg_date()
        else:
            target_date = schedule_service.parse_date_from_callback(callback_data.date)

        # Получаем данные дежурных
        duties_text = await schedule_service.get_duties_response(
            division=user.division, date=target_date, stp_repo=stp_repo
        )

        await callback.message.edit_text(
            text=duties_text,
            reply_markup=duties_kb(target_date),
        )
        await callback.answer()

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@user_schedule_router.callback_query(ScheduleMenu.filter(F.menu == "heads"))
async def heads_schedule(callback: CallbackQuery, user: User, stp_repo):
    """Обработчик расписания руководителей групп"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    try:
        current_date = get_yekaterinburg_date()
        heads_text = await schedule_service.get_heads_response(
            division=user.division, date=current_date, stp_repo=stp_repo
        )

        await callback.message.edit_text(
            text=heads_text,
            reply_markup=heads_kb(current_date),
        )

    except Exception as e:
        await schedule_service.handle_schedule_error(callback, e)


@user_schedule_router.callback_query(HeadNavigation.filter())
async def handle_head_navigation(
    callback: CallbackQuery, callback_data: HeadNavigation, user: User, stp_repo
):
    """Обработчик навигации по руководителям групп"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    try:
        action = callback_data.action

        if action == "-":
            await callback.answer()
            return

        # Определяем целевую дату
        if action == "today":
            target_date = get_yekaterinburg_date()
        else:
            target_date = schedule_service.parse_date_from_callback(callback_data.date)

        # Получаем данные руководителей групп
        heads_text = await schedule_service.get_heads_response(
            division=user.division, date=target_date, stp_repo=stp_repo
        )

        await callback.message.edit_text(
            text=heads_text,
            reply_markup=heads_kb(target_date),
        )
        await callback.answer()

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)
