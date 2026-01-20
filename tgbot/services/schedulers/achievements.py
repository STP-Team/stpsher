"""Планировщик достижений и наград.

Содержит задачи по проверке и вручению достижений пользователям,
обработке игровых механик и периодических наград.
"""

import json
import logging
import time
from datetime import date, timedelta
from enum import Enum
from typing import Dict, List, Sequence

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from stp_database.models.STP.transactions import Transaction
from stp_database.repo.Stats.requests import StatsRequestsRepo
from stp_database.repo.STP import MainRequestsRepo

from tgbot.services.broadcaster import send_message
from tgbot.services.schedulers.base import BaseScheduler

logger = logging.getLogger(__name__)

# Константы для KPI маппинга
KPI_MAPPING = {
    "AHT": {"attribute": "aht", "display_name": "AHT"},
    "CC": {"attribute": "contacts_count", "display_name": "Контактов"},
    "FLR": {"attribute": "flr", "display_name": "FLR"},
    "CSI": {"attribute": "csi", "display_name": "Оценка"},
    "POK": {"attribute": "pok", "display_name": "Отклик"},
    "DELAY": {"attribute": "delay", "display_name": "Задержка"},
    "SalesCount": {"attribute": "sales_count", "display_name": "Продаж"},
    "SalesPotential": {
        "attribute": "sales_potential",
        "display_name": "Потенциальных продаж",
    },
    "SalesConversion": {
        "attribute": "sales_conversion",
        "display_name": "Конверсия продаж",
    },
    "PaidServiceCount": {
        "attribute": "paid_service_count",
        "display_name": "Платных сервисов",
    },
    "PaidServiceConversion": {
        "attribute": "paid_service_conversion",
        "display_name": "Конверсия платного сервиса",
    },
    "SC_ONE_PERC": {
        "attribute": "target_normative_rate_first",
        "display_name": "Выполнение плана 1",
    },
    "SC_TWO_PERC": {
        "attribute": "target_normative_rate_second",
        "display_name": "Выполнение плана 2",
    },
    "PERC_THANKS": {
        "attribute": "thanks_premium",
        "display_name": "Премия за благодарности",
    },
}


def _get_kpi_value(user_kpi, kpi_name: str, user_premium=None):
    """Получает значение KPI по имени.

    Args:
        user_kpi: Объект KPI пользователя (из SpecKpi*)
        kpi_name: Имя KPI показателя
        user_premium: Объект Premium пользователя (из SpecPremium), опционально

    Returns:
        Значение KPI или None если не найдено
    """
    if kpi_name not in KPI_MAPPING:
        return None

    attribute_name = KPI_MAPPING[kpi_name]["attribute"]

    # Сначала пытаемся получить из Premium (для параметров из SpecPremium)
    if user_premium is not None:
        value = getattr(user_premium, attribute_name, None)
        if value is not None:
            return value

    # Если не найдено в Premium, пробуем получить из KPI
    return getattr(user_kpi, attribute_name, None)


async def _query_user_transactions(
    stp_repo: MainRequestsRepo, user_id: int, additional_filters: list = None
) -> Sequence[Transaction] | list:
    """Универсальная функция для запроса транзакций пользователя.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user_id: ID пользователя
        additional_filters: Дополнительные фильтры для запроса

    Returns:
        Список транзакций
    """
    try:
        # Базовые фильтры
        filters = [
            Transaction.user_id == user_id,
            Transaction.source_type == "achievement",
        ]

        # Добавляем дополнительные фильтры если есть
        if additional_filters:
            filters.extend(additional_filters)

        query = select(Transaction).filter(and_(*filters))
        result = await stp_repo.session.execute(query)
        return result.scalars().all()

    except Exception as e:
        logger.error(
            f"[Достижения] Ошибка выполнения запроса транзакций для пользователя {user_id}: {e}"
        )
        return []


def _matches_division_criteria(user_division: str, achievement_division: str) -> bool:
    """Проверяет соответствие направления пользователя критериям достижения.

    Args:
        user_division: Направление пользователя
        achievement_division: Требуемое направление для достижения

    Returns:
        True если пользователь подходит под критерии направления
    """
    if achievement_division == "ALL":
        return True

    # Если достижение для НЦК - пользователь должен быть только из НЦК
    if achievement_division == "НЦК":
        return user_division == "НЦК"

    # Если достижение для НТП - пользователь может быть из НТП1, НТП2
    if achievement_division == "НТП":
        return user_division in ["НТП1", "НТП2"]

    # Для других направлений - точное совпадение
    return user_division == achievement_division


class AchievementPeriod(Enum):
    """Периоды для проверки достижений."""

    DAILY = ("d", "spec_day_kpi", 1, "ежедневных")
    WEEKLY = ("w", "spec_week_kpi", 7, "еженедельных")
    MONTHLY = ("m", "spec_month_kpi", 30, "ежемесячных")

    def __init__(
        self, period_code: str, kpi_method: str, days_check: int, description: str
    ):
        self.period_code = period_code
        self.kpi_method = kpi_method
        self.days_check = days_check
        self.description = description


class AchievementScheduler(BaseScheduler):
    """Планировщик достижений и наград.

    Управляет задачами связанными с игровыми механиками:
    - Проверка новых достижений
    - Вручение периодических наград
    - Обновление игровой статистики
    - Уведомления о достижениях
    """

    def __init__(self):
        """Инициализация планировщика достижений."""
        super().__init__("Достижения")

    def setup_jobs(
        self,
        scheduler: AsyncIOScheduler,
        stp_session_pool: async_sessionmaker[AsyncSession],
        stats_session_pool: async_sessionmaker[AsyncSession],
        bot: Bot,
    ) -> None:
        """Настройка всех задач достижений.

        Args:
            scheduler: Экземпляр планировщика
            stp_session_pool: Пул сессий с базой STP
            bot: Экземпляр бота
            stats_session_pool:
        """
        self.logger.info("Настройка задач достижений...")

        # Настройка задач для каждого периода достижений
        for period in AchievementPeriod:
            # Основная периодическая задача
            scheduler.add_job(
                func=self._check_achievements_job,
                args=[stp_session_pool, stats_session_pool, bot, period],
                trigger="interval",
                id=f"achievements_check_{period.name.lower()}",
                name=f"Проверка {period.description} достижений",
                hours=12,
                coalesce=True,
                misfire_grace_time=300,
                replace_existing=True,
            )

            # Запуск при старте (используем run_date=None для немедленного выполнения)
            scheduler.add_job(
                func=self._check_achievements_job,
                args=[stp_session_pool, stats_session_pool, bot, period],
                trigger="date",
                id=f"achievements_startup_{period.name.lower()}",
                name=f"Запуск при старте: Проверка {period.description} достижений",
                run_date=None,
            )

    async def _check_achievements_job(
        self, stp_session_pool, stats_session_pool, bot: Bot, period: AchievementPeriod
    ) -> None:
        """Универсальная проверка достижений для любого периода.

        Args:
            stp_session_pool: Пул сессий с базой STP
            stats_session_pool: Пул сессий с базой KPI
            bot: Экземпляр бота
            period: Период достижений для проверки
        """
        job_name = f"Проверка {period.description} достижений"
        start_time = time.time()

        self._log_job_execution_start(job_name)
        try:
            stats = await check_achievements(
                stp_session_pool, stats_session_pool, bot, period
            )
            execution_time = time.time() - start_time

            logger.info(
                f"[Достижения] {job_name} завершена за {execution_time:.2f}с. "
                f"Пользователей: {stats['users_processed']}, "
                f"Достижений вручено: {stats['achievements_awarded']}, "
                f"Ошибок: {stats['errors']}"
            )

            self._log_job_execution_end(job_name, success=True)
        except Exception as e:
            self._log_job_execution_end(job_name, success=False, error=str(e))


async def check_achievements(
    stp_session_pool: async_sessionmaker[AsyncSession],
    stats_session_pool: async_sessionmaker[AsyncSession],
    bot: Bot,
    period: AchievementPeriod,
) -> Dict[str, int]:
    """Универсальная проверка и вручение достижений для любого периода.

    Args:
        stp_session_pool: Пул сессий с базой STP
        stats_session_pool: Пул сессий с базой KPI
        bot: Экземпляр бота
        period: Период для проверки достижений

    Returns:
        Статистика выполнения: users_processed, achievements_awarded, errors
    """
    stats = {"users_processed": 0, "achievements_awarded": 0, "errors": 0}

    try:
        async with (
            stp_session_pool() as stp_session,
            stats_session_pool() as stats_session,
        ):
            stp_repo = MainRequestsRepo(stp_session)
            stats_repo = StatsRequestsRepo(stats_session)

            # Получаем всех пользователей одним запросом
            playing_users = await stp_repo.employee.get_users(roles=[1, 3, 10])
            if not playing_users:
                logger.info("[Достижения] Нет пользователей в базе данных")
                return stats

            # Получаем все достижения для периода одним запросом
            all_achievements = await stp_repo.achievement.get_achievements()
            period_achievements = [
                ach for ach in all_achievements if ach.period == period.period_code
            ]

            if not period_achievements:
                logger.info(
                    f"[Достижения] Нет {period.description} достижений в базе данных"
                )
                return stats

            logger.info(
                f"[Достижения] Проверка {len(period_achievements)} {period.description} достижений "
                f"для {len(playing_users)} пользователей"
            )

            # Обрабатываем всех пользователей
            for user in playing_users:
                try:
                    stats["users_processed"] += 1

                    # Проверяем достижения для пользователя
                    earned_achievements = await _check_user_achievements(
                        stp_repo, stats_repo, user, period_achievements, period
                    )

                    if earned_achievements:
                        await _award_achievements(
                            stp_repo, user, earned_achievements, bot
                        )
                        stats["achievements_awarded"] += len(earned_achievements)

                except Exception as e:
                    stats["errors"] += 1
                    logger.error(
                        f"[Достижения] Ошибка проверки {period.description} достижений "
                        f"для пользователя {user.fullname}: {e}"
                    )
                    continue

            logger.info(
                f"[Достижения] Вручено {stats['achievements_awarded']} {period.description} достижений"
            )

    except Exception as e:
        stats["errors"] += 1
        logger.error(
            f"[Достижения] Критическая ошибка при проверке {period.description} достижений: {e}"
        )
        raise

    return stats


# Вспомогательные функции
async def _check_user_achievements(
    stp_repo: MainRequestsRepo,
    stats_repo: StatsRequestsRepo,
    user,
    achievements_list: List,
    period: AchievementPeriod,
) -> List[Dict]:
    """Проверка достижений для конкретного пользователя.

    Args:
        stp_repo: Репозиторий операций с базой STP
        stats_repo: Репозиторий операций с базой KPI
        user: Экземпляр пользователя с моделью Employee
        achievements_list: Список доступных достижений
        period: Период для проверки

    Returns:
        Список новых достижений для вручения
    """
    earned_achievements = []

    try:
        if not user.user_id:
            return earned_achievements

        # Динамически получаем нужный KPI метод
        kpi_method = getattr(stats_repo, period.kpi_method, None)
        if not kpi_method:
            logger.error(
                f"[Достижения] Метод KPI {period.kpi_method} не найден для периода {period.name}"
            )
            return earned_achievements

        # Получаем KPI пользователя за период
        user_kpi = await kpi_method.get_kpi(user.fullname)
        if not user_kpi:
            logger.debug(
                f"[Достижения] Нет {period.description} KPI данных для пользователя {user.fullname}"
            )
            return earned_achievements

        # Получаем extraction_period из KPI данных
        extraction_period = user_kpi.extraction_period
        if not extraction_period:
            logger.debug(
                f"[Достижения] Нет extraction_period в {period.description} KPI данных для пользователя {user.fullname}"
            )
            return earned_achievements

        # Получаем SpecPremium данные для параметров из премиальной таблицы
        user_premium = await stats_repo.spec_premium.get_premium(user.fullname, extraction_period)

        # Получаем существующие достижения одним запросом
        (
            existing_transactions,
            recent_transactions,
        ) = await _get_user_achievement_history(
            stp_repo, user.user_id, extraction_period, period.days_check
        )

        existing_achievement_ids = {
            t.source_id for t in existing_transactions if t.source_id
        }
        recent_achievement_ids = {
            t.source_id for t in recent_transactions if t.source_id
        }

        # Проверяем каждое доступное достижение
        for achievement in achievements_list:
            try:
                # Пропускаем достижение если уже получено с этим kpi_extracted_at
                if achievement.id in existing_achievement_ids:
                    logger.debug(
                        f"[Достижения] Достижение {achievement.name} уже получено для extraction_period {extraction_period}"
                    )
                    continue

                # Пропускаем если достижение было получено за последний период
                if achievement.id in recent_achievement_ids:
                    logger.debug(
                        f"[Достижения] Достижение {achievement.name} уже получено за последний период ({period.description})"
                    )
                    continue

                # Проверяем соответствие пользователя критериям достижения
                if not _user_matches_achievement_criteria(user, achievement):
                    continue

                # Проверяем KPI критерии
                if await _check_kpi_criteria(user_kpi, achievement.kpi, user_premium):
                    earned_achievements.append({
                        "id": achievement.id,
                        "name": achievement.name,
                        "description": achievement.description,
                        "reward_points": achievement.reward,
                        "kpi_values": _get_user_kpi_values(user_kpi, achievement.kpi, user_premium),
                        "extraction_period": extraction_period,
                    })
                    logger.info(
                        f"[Достижения] Пользователь {user.fullname} заработал {period.description[:-2]}ое достижение '{achievement.name}'"
                    )

            except Exception as e:
                logger.error(
                    f"[Достижения] Ошибка проверки достижения {achievement.name} для {user.fullname}: {e}"
                )
                continue

    except Exception as e:
        logger.error(
            f"[Достижения] Ошибка проверки {period.description} достижений пользователя {user.fullname}: {e}"
        )

    return earned_achievements


async def _get_user_achievement_history(
    stp_repo: MainRequestsRepo, user_id: int, extraction_period, days_check: int
) -> tuple[Sequence[Transaction], Sequence[Transaction]]:
    """Получает историю достижений пользователя одним запросом.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user_id: ID пользователя
        extraction_period: Дата извлечения KPI
        days_check: Количество дней для проверки дублирования

    Returns:
        Tuple из существующих достижений с той же датой KPI и недавних достижений
    """
    try:
        # Получаем достижения с определенной датой KPI
        existing_transactions = await _get_user_achievements_by_kpi_date(
            stp_repo, user_id, extraction_period
        )

        # Получаем достижения за последние N дней
        recent_transactions = await _get_user_achievements_last_n_days(
            stp_repo, user_id, days_check
        )

        return existing_transactions, recent_transactions

    except Exception as e:
        logger.error(
            f"[Достижения] Ошибка получения истории достижений для пользователя {user_id}: {e}"
        )
        return [], []


async def _award_achievements(
    stp_repo: MainRequestsRepo, user, achievements: List[Dict], bot: Bot
):
    """Вручение достижений пользователю.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee
        achievements: Список достижений для вручения
        bot: Экземпляр бота
    """
    try:
        successful_achievements = []
        total_reward = 0
        final_balance = None

        # Сначала создаем все транзакции
        for achievement in achievements:
            # Создаем транзакцию в БД
            comment = f'Достижение "{achievement["name"]}". Выполненный показатель: {_format_kpi_values(achievement["kpi_values"])}'

            transaction, new_balance = await stp_repo.transaction.add_transaction(
                user_id=user.user_id,
                transaction_type="earn",
                source_type="achievement",
                amount=achievement["reward_points"],
                source_id=achievement["id"],
                comment=comment,
                kpi_extracted_at=achievement.get("extraction_period"),
            )

            if transaction:
                successful_achievements.append(achievement)
                total_reward += achievement["reward_points"]
                final_balance = new_balance  # Сохраняем финальный баланс

                logger.debug(
                    f"[Достижения] Вручено достижение '{achievement['name']}' ({achievement['reward_points']} баллов) пользователю {user.fullname}"
                )
            else:
                logger.error(
                    f"[Достижения] Не удалось создать транзакцию для достижения '{achievement['name']}' пользователю {user.fullname}"
                )

        # Отправляем одно уведомление обо всех полученных достижениях
        if successful_achievements:
            logger.debug(
                f"[Достижения] Отправка уведомления о {len(successful_achievements)} достижениях ({total_reward} баллов) пользователю {user.fullname}"
            )
            message = _create_batch_achievements_message(
                successful_achievements, total_reward, final_balance
            )
            success = await send_message(bot, user.user_id, message)

            if success:
                logger.debug(
                    f"[Достижения] Уведомление успешно отправлено пользователю {user.fullname}"
                )
            else:
                logger.debug(
                    f"[Достижения] Не удалось отправить уведомление пользователю {user.fullname} (возможно, пользователь не начал диалог с ботом)"
                )

    except Exception as e:
        logger.error(
            f"[Достижения] Ошибка вручения достижений пользователю {user.fullname}: {e}"
        )


async def _get_user_achievements_by_kpi_date(
    stp_repo: MainRequestsRepo, user_id: int, extraction_period
) -> Sequence[Transaction] | list:
    """Получает достижения пользователя с определенным kpi_extracted_at.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user_id: ID пользователя
        extraction_period: Дата извлечения KPI

    Returns:
        Список транзакций-достижений с указанным kpi_extracted_at
    """
    additional_filters = [Transaction.kpi_extracted_at == extraction_period]
    return await _query_user_transactions(stp_repo, user_id, additional_filters)


async def _get_user_achievements_last_n_days(
    stp_repo: MainRequestsRepo, user_id: int, n_days: int
) -> Sequence[Transaction] | list:
    """Получает достижения пользователя за последние n дней.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user_id: ID пользователя
        n_days: Количество дней назад

    Returns:
        Список транзакций-достижений за последние n дней
    """
    # Вычисляем дату n дней назад
    cutoff_date = date.today() - timedelta(days=n_days)
    additional_filters = [func.date(Transaction.created_at) >= cutoff_date]
    return await _query_user_transactions(stp_repo, user_id, additional_filters)


def _user_matches_achievement_criteria(user, achievement) -> bool:
    """Проверяет соответствие пользователя критериям достижения.

    Args:
        user: Экземпляр пользователя с моделью Employee
        achievement:

    Returns:
        True если пользователь подходит под критерии
    """
    try:
        # Проверяем направление через унифицированную функцию
        if not _matches_division_criteria(user.division, achievement.division):
            return False

        # Проверяем позицию (точное совпадение)
        if achievement.position != "ALL" and user.position != achievement.position:
            return False

        return True

    except Exception as e:
        logger.error(
            f"[Достижения] Ошибка проверки критериев достижения {achievement.name}: {e}"
        )
        return False


async def _check_kpi_criteria(user_kpi, kpi_criteria_str: str, user_premium=None) -> bool:
    """Проверяет соответствие KPI пользователя критериям достижения.

    Args:
        user_kpi: KPI пользователя за день
        kpi_criteria_str: JSON строка с критериями (например: {"AHT":[0,740],"CC":[20,99999]})
        user_premium: Premium пользователя из SpecPremium, опционально

    Returns:
        True если KPI соответствует критериям
    """
    try:
        kpi_criteria = json.loads(kpi_criteria_str)

        for kpi_name, criteria_range in kpi_criteria.items():
            min_val, max_val = criteria_range[0], criteria_range[1]

            # Получаем значение KPI пользователя через унифицированную функцию
            user_value = _get_kpi_value(user_kpi, kpi_name, user_premium)

            if user_value is None:
                logger.debug(
                    f"[Достижения] Нет данных по KPI {kpi_name} для пользователя"
                )
                return False

            # Проверяем диапазон
            if not (min_val <= user_value <= max_val):
                return False

        return True

    except Exception as e:
        logger.error(f"[Достижения] Ошибка проверки KPI критериев: {e}")
        return False


def _get_user_kpi_values(user_kpi, kpi_criteria_str: str, user_premium=None) -> Dict:
    """Получает актуальные значения KPI пользователя согласно критериям.

    Args:
        user_kpi: KPI пользователя за день
        kpi_criteria_str: JSON строка с критериями
        user_premium: Premium пользователя из SpecPremium, опционально

    Returns:
        Словарь с актуальными значениями KPI
    """
    kpi_values = {}

    try:
        kpi_criteria = json.loads(kpi_criteria_str)

        for kpi_name in kpi_criteria.keys():
            # Получаем отображаемое название и значение через унифицированные функции
            display_name = KPI_MAPPING.get(kpi_name, {}).get("display_name", kpi_name)
            kpi_value = _get_kpi_value(user_kpi, kpi_name, user_premium)

            if kpi_value is not None:
                kpi_values[display_name] = kpi_value

    except Exception as e:
        logger.error(f"[Достижения] Ошибка получения значений KPI: {e}")

    return kpi_values


def _format_kpi_values(kpi_values: Dict) -> str:
    """Форматирует KPI значения в читаемую строку.

    Args:
        kpi_values: Словарь с KPI значениями

    Returns:
        Отформатированная строка
    """
    kpi_parts = []
    for kpi_name, value in kpi_values.items():
        if value is not None:
            if isinstance(value, float):
                # Убираем лишние нули после запятой для целых чисел
                if value.is_integer():
                    formatted_value = str(int(value))
                else:
                    formatted_value = f"{value:g}"
            else:
                formatted_value = str(value)
            kpi_parts.append(f"{kpi_name} {formatted_value}")
    return ", ".join(kpi_parts)


def _add_kpi_info_to_message(
    message_parts: List[str], achievement: Dict, prefix: str = "Твои показатели: "
) -> None:
    """Добавляет информацию о KPI в сообщение.

    Args:
        message_parts: Список частей сообщения для изменения
        achievement: Достижение с KPI значениями
        prefix: Префикс для отображения KPI
    """
    if achievement.get("kpi_values"):
        formatted_kpi = _format_kpi_values(achievement["kpi_values"])
        if formatted_kpi:
            message_parts.append(f"{prefix}{formatted_kpi}")


def _create_achievement_message(achievement: Dict, new_balance: int = None) -> str:
    """Создание сообщения о получении достижения.

    Args:
        achievement: Достижение с моделью Achievement
        new_balance: Новый баланс пользователя

    Returns:
        Текст сообщения
    """
    message_parts = [
        "🏆 <b>Новое достижение!</b>\n",
        f"🎉 <b>{achievement['name']}: {achievement['reward_points']} балла за {achievement['description']}</b>\n",
    ]

    # Показываем KPI показатели
    _add_kpi_info_to_message(message_parts, achievement)

    if new_balance is not None:
        message_parts.append(f"Новый баланс: {new_balance} баллов")

    message_parts.append("\n✨ Поздравляем с новым достижением!")

    return "\n".join(message_parts)


def _create_batch_achievements_message(
    achievements: List[Dict], total_reward: int, final_balance: int = None
) -> str:
    """Создание сообщения о получении нескольких достижений.

    Args:
        achievements: Список достижений
        total_reward: Общая сумма наград
        final_balance: Итоговый баланс пользователя

    Returns:
        Текст сообщения
    """
    if len(achievements) == 1:
        # Если достижение одно, используем стандартное сообщение
        return _create_achievement_message(achievements[0], final_balance)

    message_parts = [f"🏆 <b>Получено достижений: {len(achievements)}</b>\n"]

    # Список всех достижений
    for i, achievement in enumerate(achievements, 1):
        message_parts.append(
            f"{i}. 🎉 <b>{achievement['name']}</b> (+{achievement['reward_points']} баллов)"
        )
        if achievement.get("description"):
            message_parts.append(f"   📝 {achievement['description']}")

        # Показываем KPI показатели через унифицированную функцию
        _add_kpi_info_to_message(message_parts, achievement, "   📊 Твои показатели: ")

        message_parts.append("")  # Пустая строка между достижениями

    message_parts.append(f"💰 <b>Общая награда: {total_reward} баллов</b>")

    if final_balance is not None:
        message_parts.append(f"💎 Текущий баланс: {final_balance} баллов")

    message_parts.append("\n✨ Поздравляем с новыми достижениями!")

    return "\n".join(message_parts)
