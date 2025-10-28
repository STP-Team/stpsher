"""Сервис обработчиков расписаний - Оптимизирован.

Модуль предоставляет главный сервис для обработки операций с расписаниями,
включая графики сотрудников, дежурных, руководителей и групповые графики.
"""

import datetime
import logging
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from stp_database import Employee, MainRequestsRepo

from tgbot.keyboards.auth import auth_kb

from ..core.analyzers import ScheduleAnalyzer
from ..core.exceptions import (
    ScheduleError,
    ScheduleFileNotFoundError,
    UserNotFoundError,
)
from ..formatters.schedule import ScheduleFormatter, get_current_date
from ..parsers.schedule import (
    DutyScheduleParser,
    GroupScheduleParser,
    HeadScheduleParser,
    ScheduleParser,
)

logger = logging.getLogger(__name__)


class ScheduleHandlerService:
    """Сервис для обработки операций с расписаниями."""

    def __init__(self) -> None:
        """Инициализирует сервис обработчика расписаний со всеми необходимыми парсерами."""
        self.schedule_parser = ScheduleParser()
        self.duty_parser = DutyScheduleParser()
        self.head_parser = HeadScheduleParser()
        self.group_parser = GroupScheduleParser()
        self.formatter = ScheduleFormatter()
        self.analyzer = ScheduleAnalyzer()

    @staticmethod
    async def check_user_auth(callback: CallbackQuery, user: Employee) -> bool:
        """Проверяет авторизацию пользователя.

        Args:
            callback: Callback query от Telegram
            user: Экземпляр пользователя с моделью Employee

        Returns:
            Статус авторизации пользователя
        """
        if not user:
            await callback.message.answer(
                """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
                reply_markup=auth_kb(),
            )
            return False
        return True

    @staticmethod
    async def handle_schedule_error(
        callback: CallbackQuery,
        error: Exception,
        fallback_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> None:
        """Обработка ошибок расписания.

        Args:
            callback: Callback query от Telegram
            error: Ошибка от Python
            fallback_markup: Клавиатура для отображения при ошибке

        Returns:
            None
        """
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

    async def get_user_schedule_response(
        self,
        user: Employee,
        month: str,
        compact: bool = True,
        stp_repo: MainRequestsRepo = None,
        bot: Bot = None,
    ) -> str:
        """Получает расписание пользователя.

        Args:
            user: Объект сотрудника
            month: Название месяца
            compact: Использовать компактный формат
            stp_repo: Репозиторий базы данных
            bot: Экземпляр бота для создания ссылок

        Returns:
            Отформатированная строка с расписанием
        """
        try:
            if stp_repo:
                # График с дежурными
                return (
                    await self.schedule_parser.get_user_schedule_formatted_with_duties(
                        fullname=user.fullname,
                        month=month,
                        division=user.division,
                        compact=compact,
                        stp_repo=stp_repo,
                        bot=bot,
                    )
                )
            else:
                # Обычный график
                return self.schedule_parser.get_user_schedule_formatted(
                    fullname=user.fullname,
                    month=month,
                    division=user.division,
                    compact=compact,
                )

        except Exception as e:
            logger.error(f"Schedule error (optimized): {e}", exc_info=True)
            return f"❌ <b>Ошибка графика:</b>\n<code>{e}</code>"

    async def get_duties_response(
        self, division: str, date: Optional[datetime.datetime] = None, stp_repo=None
    ) -> str:
        """Получает расписание дежурных.

        Args:
            division: Направление
            date: Дата (по умолчанию текущая)
            stp_repo: Репозиторий базы данных

        Returns:
            Отформатированная строка с дежурствами
        """
        if date is None:
            date = get_current_date()

        duties = await self.duty_parser.get_duties_for_date(date, division, stp_repo)

        # Check if today's date is selected to highlight current duties
        today = get_current_date()
        highlight_current = (date.date() == today.date()) and stp_repo

        # Get formatted duties files_processing with optional current duty highlighting
        return await self.duty_parser.format_schedule(
            duties, date, highlight_current, division, stp_repo
        )

    async def get_heads_response(
        self, division: str, date: Optional[datetime.datetime] = None, stp_repo=None
    ) -> str:
        """Получает расписание руководителей групп.

        Args:
            division: Направление
            date: Дата (по умолчанию текущая)
            stp_repo: Репозиторий базы данных

        Returns:
            Отформатированная строка с руководителями
        """
        if date is None:
            date = get_current_date()

        heads = await self.head_parser.get_heads_for_date(date, division, stp_repo)

        return self.head_parser.format_schedule(heads, date)

    async def get_group_schedule_response(
        self,
        user: Employee,
        date: Optional[datetime.datetime] = None,
        page: int = 1,
        stp_repo=None,
        is_head: bool = False,
    ) -> Tuple[str, int, bool, bool]:
        """Получает групповое расписание для пользователя или руководителя.

        Args:
            user: Объект сотрудника
            date: Дата (по умолчанию текущая)
            page: Номер страницы для пагинации
            stp_repo: Репозиторий базы данных
            is_head: Является ли пользователь руководителем

        Returns:
            Кортеж (текст, всего_страниц, есть_предыдущая, есть_следующая)
        """
        if date is None:
            date = get_current_date()

        try:
            if is_head:
                # Для руководителя - показываем его группу
                group_members = await self.group_parser.get_group_members(
                    user.fullname, date, user.division, stp_repo
                )
                return self.group_parser.format_group_schedule_for_head(
                    date, group_members, page
                )
            else:
                # Для обычного пользователя - показываем коллег по группе
                group_members = await self.group_parser.get_group_members_for_user(
                    user.fullname, date, user.division, stp_repo
                )
                return self.group_parser.format_group_schedule_for_user(
                    date, group_members, page
                )

        except Exception as e:
            logger.error(f"Ошибка получения группового расписания: {e}")
            return "❌ Ошибка получения расписания группы", 1, False, False


# Создаем единственный экземпляр сервиса
schedule_service = ScheduleHandlerService()
