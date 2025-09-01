import logging
from typing import Optional, Sequence, TypedDict, Unpack
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.STP.schedules import Schedules
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class ScheduleLogParams(TypedDict, total=False):
    """Доступные параметры для создания/обновления записи ScheduleLog."""

    file_id: str
    file_name: str
    file_size: int
    uploaded_by_user_id: int


class ScheduleLogRepo(BaseRepo):
    async def get_files_history(
        self,
        file_id: Optional[str] = None,
        uploaded_by_user_id: Optional[int] = None,
        uploaded_from: Optional[datetime] = None,
        uploaded_to: Optional[datetime] = None,
    ) -> Sequence[Schedules]:
        """
        Получить записи лога расписания по фильтрам.

        Args:
            file_id: Идентификатор Telegram файла
            uploaded_by_user_id: ID пользователя, загрузившего файл
            uploaded_from: Начало периода времени загрузки
            uploaded_to: Конец периода времени загрузки

        Returns:
            Список объектов ScheduleLog
        """
        filters = []

        if file_id:
            filters.append(Schedules.file_id == file_id)
        if uploaded_by_user_id:
            filters.append(Schedules.uploaded_by_user_id == uploaded_by_user_id)
        if uploaded_from:
            filters.append(Schedules.uploaded_at >= uploaded_from)
        if uploaded_to:
            filters.append(Schedules.uploaded_at <= uploaded_to)

        query = select(Schedules).order_by(Schedules.uploaded_at.desc())
        if filters:
            query = query.where(and_(*filters))

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения записей ScheduleLog: {e}")
            return []

    async def add_file_history(
        self, **kwargs: Unpack[ScheduleLogParams]
    ) -> Optional[Schedules]:
        """
        Добавить новую запись в логи расписания.

        Args:
            kwargs: Параметры для создания записи ScheduleLog

        Returns:
            Новый объект ScheduleLog или None при ошибке
        """
        file_entry = Schedules(**kwargs)
        self.session.add(file_entry)
        try:
            await self.session.commit()
            await self.session.refresh(file_entry)
            return file_entry
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка добавления записи ScheduleLog: {e}")
            await self.session.rollback()
            return None
