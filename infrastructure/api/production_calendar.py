"""API для получения производственного календаря."""

import datetime
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Set

import httpx

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Запись в кеше с данными и временем истечения.

    Attributes:
        data: Кешированные данные
        expires_at: Время истечения кеша
    """

    data: Dict[datetime.date, str]
    expires_at: datetime.datetime


class ProductionCalendarAPI:
    """API для получения данных о производственном календаре.

    Класс предоставляет асинхронные методы для работы с производственным
    календарем, включая получение списка праздников, проверку дат и
    получение названий праздников.

    Attributes:
        base_url: Базовый URL API производственного календаря
        timeout: Таймаут для HTTP запросов в секундах
        cache_ttl: Время жизни кеша в секундах
    """

    def __init__(
        self,
        base_url: str = "https://calendar.kuzyak.in/api/calendar",
        timeout: float = 10.0,
        cache_ttl: int = 86400,  # 24 часа
    ):
        """Инициализирует API клиент производственного календаря.

        Args:
            base_url: Базовый URL API. По умолчанию calendar.kuzyak.in
            timeout: Таймаут для HTTP запросов в секундах. По умолчанию 10
            cache_ttl: Время жизни кеша в секундах. По умолчанию 86400 (24ч)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._cache: Dict[int, CacheEntry] = {}

    async def _fetch_holidays_data(
        self, year: int
    ) -> Optional[Dict[datetime.date, str]]:
        """Получает данные о праздниках с API с повторными попытками.

        Args:
            year: Год для получения данных

        Returns:
            Словарь с датами праздников и их названиями или None при ошибке.
        """
        url = f"{self.base_url}/{year}/holidays"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(3):
                try:
                    response = await client.get(url)
                    response.raise_for_status()

                    data = response.json()
                    holidays_info = {}

                    for holiday in data.get("holidays", []):
                        date_str = holiday.get("date")
                        name = holiday.get("name")

                        if not date_str or not name:
                            logger.warning(
                                f"Пропущена запись с неполными данными: {holiday}"
                            )
                            continue

                        # Парсим ISO дату (2025-01-01T00:00:00.000Z)
                        try:
                            date_obj = datetime.datetime.fromisoformat(
                                date_str.replace("Z", "+00:00")
                            ).date()
                            holidays_info[date_obj] = name
                        except ValueError as ve:
                            logger.warning(
                                f"Не удалось распарсить дату {date_str}: {ve}"
                            )
                            continue

                    logger.debug(
                        f"Загружена информация о {len(holidays_info)} праздниках для {year} года"
                    )
                    return holidays_info

                except httpx.HTTPStatusError as e:
                    logger.error(
                        f"HTTP ошибка при запросе календаря (попытка {attempt + 1}/3): {e}"
                    )
                    if attempt == 2:  # Последняя попытка
                        return None

                except httpx.RequestError as e:
                    logger.error(
                        f"Ошибка сети при запросе календаря (попытка {attempt + 1}/3): {e}"
                    )
                    if attempt == 2:  # Последняя попытка
                        return None

                except Exception as e:
                    logger.error(
                        f"Неожиданная ошибка при запросе календаря для {year} года: {e}"
                    )
                    return None

        return None

    def _is_cache_valid(self, year: int) -> bool:
        """Проверяет валидность кеша для указанного года.

        Args:
            year: Год для проверки

        Returns:
            True если кеш валиден, False в противном случае.
        """
        if year not in self._cache:
            return False
        return datetime.datetime.now() < self._cache[year].expires_at

    async def get_holiday_info(self, year: int) -> Optional[Dict[datetime.date, str]]:
        """Получает информацию о праздниках с их названиями.

        Args:
            year: Год для получения праздников

        Returns:
            Словарь где ключ - дата праздника, значение - название праздника.
            None если произошла ошибка при получении данных.

        Examples:
            >>> import asyncio
            >>> calendar = ProductionCalendarAPI()
            >>> holidays = asyncio.run(calendar.get_holiday_info(2025))
            >>> print(holidays[datetime.date(2025, 1, 1)])
            'Новый год'
        """
        if self._is_cache_valid(year):
            return self._cache[year].data

        holidays_info = await self._fetch_holidays_data(year)

        if holidays_info is not None:
            expires_at = datetime.datetime.now() + datetime.timedelta(
                seconds=self.cache_ttl
            )
            self._cache[year] = CacheEntry(data=holidays_info, expires_at=expires_at)

        return holidays_info

    async def get_holidays(self, year: int) -> Optional[Set[datetime.date]]:
        """Получает список праздничных дней для указанного года.

        Args:
            year: Год для получения праздничных дней

        Returns:
            Множество праздничных дат или None при ошибке.

        Examples:
            >>> import asyncio
            >>> calendar = ProductionCalendarAPI()
            >>> holidays = asyncio.run(calendar.get_holidays(2025))
            >>> datetime.date(2025, 1, 1) in holidays
            True
        """
        holidays_info = await self.get_holiday_info(year)
        if holidays_info is None:
            return None
        return set(holidays_info.keys())

    async def is_holiday(self, date: datetime.date) -> bool:
        """Проверяет, является ли указанная дата праздничной.

        Args:
            date: Дата для проверки

        Returns:
            True если дата является праздником, False в противном случае.
            При ошибке получения данных возвращает False.

        Examples:
            >>> import asyncio
            >>> calendar = ProductionCalendarAPI()
            >>> asyncio.run(calendar.is_holiday(datetime.date(2025, 1, 1)))
            True
            >>> asyncio.run(calendar.is_holiday(datetime.date(2025, 1, 15)))
            False
        """
        holidays = await self.get_holidays(date.year)
        if holidays is None:
            return False
        return date in holidays

    async def get_holiday_name(self, date: datetime.date) -> Optional[str]:
        """Получает название праздника для указанной даты.

        Args:
            date: Дата праздника

        Returns:
            Название праздника если дата является праздником, None в противном случае.

        Examples:
            >>> import asyncio
            >>> calendar = ProductionCalendarAPI()
            >>> asyncio.run(calendar.get_holiday_name(datetime.date(2025, 1, 1)))
            'Новый год'
            >>> asyncio.run(calendar.get_holiday_name(datetime.date(2025, 1, 15)))
            None
        """
        holidays_info = await self.get_holiday_info(date.year)
        if holidays_info is None:
            return None
        return holidays_info.get(date)

    def clear_cache(self, year: Optional[int] = None) -> None:
        """Очищает кеш для указанного года или весь кеш.

        Args:
            year: Год для очистки кеша. Если None, очищает весь кеш

        Examples:
            >>> calendar = ProductionCalendarAPI()
            >>> calendar.clear_cache(2025)  # Очистить только 2025
            >>> calendar.clear_cache()  # Очистить весь кеш
        """
        if year is None:
            self._cache.clear()
            logger.debug("Кеш производственного календаря полностью очищен")
        elif year in self._cache:
            del self._cache[year]
            logger.debug(f"Кеш производственного календаря для {year} года очищен")


# Создаем глобальный экземпляр API
production_calendar = ProductionCalendarAPI()
