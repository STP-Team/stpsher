import datetime
import logging
from typing import Dict, Optional, Set

import requests

logger = logging.getLogger(__name__)


class ProductionCalendarAPI:
    """API для получения данных о производственном календаре"""

    def __init__(self):
        self.base_url = "https://calendar.kuzyak.in/api/calendar"
        self._holidays_cache: Dict[int, Set[datetime.date]] = {}

    async def get_holidays(self, year: int) -> Optional[Set[datetime.date]]:
        """Получает список праздничных дней для указанного года

        :param year: Год
        :return: Множество праздничных дат или None при ошибке
        """
        if year in self._holidays_cache:
            return self._holidays_cache[year]

        try:
            response = requests.get(f"{self.base_url}/{year}/holidays")
            response.raise_for_status()

            data = response.json()
            holidays = set()

            for holiday in data.get("holidays", []):
                date_str = holiday["date"]
                # Парсим ISO дату (2025-01-01T00:00:00.000Z)
                date_obj = datetime.datetime.fromisoformat(
                    date_str.replace("Z", "+00:00")
                ).date()
                holidays.add(date_obj)

            self._holidays_cache[year] = holidays
            logger.debug(f"Загружено {len(holidays)} праздничных дней для {year} года")
            return holidays

        except Exception as e:
            logger.error(f"Ошибка получения праздничных дней для {year} года: {e}")
            return None

    async def get_holiday_info(self, year: int) -> Optional[Dict[datetime.date, str]]:
        """Получает информацию о праздниках с их названиями

        :param year: Год
        :return: Словарь {дата: название праздника} или None при ошибке
        """
        try:
            response = requests.get(f"{self.base_url}/{year}/holidays")
            response.raise_for_status()

            data = response.json()
            holidays_info = {}

            for holiday in data.get("holidays", []):
                date_str = holiday["date"]
                name = holiday["name"]
                # Парсим ISO дату
                date_obj = datetime.datetime.fromisoformat(
                    date_str.replace("Z", "+00:00")
                ).date()
                holidays_info[date_obj] = name

            logger.debug(
                f"Загружена информация о {len(holidays_info)} праздниках для {year} года"
            )
            return holidays_info

        except Exception as e:
            logger.error(
                f"Ошибка получения информации о праздниках для {year} года: {e}"
            )
            return None

    async def is_holiday(self, date: datetime.date) -> bool:
        """Проверяет, является ли указанная дата праздничной

        :param date: Дата для проверки
        :return: True если праздник, False если нет
        """
        holidays = await self.get_holidays(date.year)
        if holidays is None:
            return False
        return date in holidays

    async def get_holiday_name(self, date: datetime.date) -> Optional[str]:
        """Получает название праздника для указанной даты

        :param date: Дата
        :return: Название праздника или None если не праздник
        """
        holidays_info = await self.get_holiday_info(date.year)
        if holidays_info is None:
            return None
        return holidays_info.get(date)


# Создаем глобальный экземпляр API
production_calendar = ProductionCalendarAPI()
