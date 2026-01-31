"""Планировщик достижений и наград.

Содержит задачи по проверке и вручению достижений пользователям,
обработке игровых механик и периодических наград.
"""

import json
import logging
import time
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List

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
    "CSAT": {"attribute": "csat", "display_name": "CSAT", "from_premium": False},
    "CSAT_HIGH_RATED": {
        "attribute": "csat_high_rated",
        "display_name": "CSAT Кол-во высоких оценок",
        "from_premium": False,
    },
    "CSAT_RATED": {
        "attribute": "csat_rated",
        "display_name": "CSAT Кол-во оценок",
        "from_premium": False,
    },
    "AHT": {"attribute": "aht", "display_name": "AHT", "from_premium": False},
    "CC": {
        "attribute": "contacts_count",
        "display_name": "Контактов",
        "from_premium": False,
    },
    "FLR": {"attribute": "flr", "display_name": "FLR", "from_premium": False},
    "CSI": {"attribute": "csi", "display_name": "Оценка", "from_premium": False},
    "POK": {"attribute": "pok", "display_name": "Отклик", "from_premium": False},
    "DELAY": {"attribute": "delay", "display_name": "Задержка", "from_premium": False},
    "SalesCount": {
        "attribute": "sales",
        "display_name": "Продаж",
        "from_premium": False,
    },
    "SalesPotential": {
        "attribute": "sales_potential",
        "display_name": "Потенциальных продаж",
        "from_premium": False,
    },
    "SalesConversion": {
        "attribute": "sales_conversion",
        "display_name": "Конверсия продаж",
        "from_premium": False,
    },
    "PaidServiceCount": {
        "attribute": "services",
        "display_name": "Платных сервисов",
        "from_premium": False,
    },
    "PaidServiceConversion": {
        "attribute": "services_conversion",
        "display_name": "Конверсия платного сервиса",
        "from_premium": False,
    },
    "GOK": {"attribute": "gok", "display_name": "ГОК", "from_premium": True},
}


def _get_kpi_value(user_kpi, kpi_name: str, user_premium=None):
    """Получает значение KPI по имени.

    Args:
        user_kpi: Объект KPI пользователя (из SpecKpi*)
        kpi_name: Имя KPI показателя
        user_premium: Объект Premium пользователя из SpecPremium, опционально

    Returns:
        Значение KPI или None если не найдено
    """
    if kpi_name not in KPI_MAPPING:
        return None

    kpi_config = KPI_MAPPING[kpi_name]
    attribute_name = kpi_config["attribute"]
    from_premium = kpi_config.get("from_premium", False)

    # Проверяем Premium только если флаг from_premium=True
    if from_premium and user_premium is not None:
        value = getattr(user_premium, attribute_name, None)
        if value is not None:
            return value

    # Получаем из KPI (по умолчанию или если не найдено в Premium)
    return getattr(user_kpi, attribute_name, None)


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

            # Запуск при старте (одноразовая задача)
            scheduler.add_job(
                func=self._check_achievements_job,
                args=[stp_session_pool, stats_session_pool, bot, period],
                trigger="date",
                id=f"achievements_startup_{period.name.lower()}",
                name=f"Запуск при старте: Проверка {period.description} достижений",
                run_date=None,  # Выполнить немедленно при запуске планировщика
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

        self._log_job_execution(job_name, True)
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

            self._log_job_execution(job_name, True)

        except Exception as e:
            self._log_job_execution(job_name, False, str(e))


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

            # Индексируем достижения по критериям для быстрого поиска
            achievements_index = _build_achievements_index(period_achievements)

            logger.info(
                f"[Достижения] Проверка {len(period_achievements)} {period.description} достижений "
                f"для {len(playing_users)} пользователей"
            )

            # Пакетная загрузка данных KPI для всех пользователей
            kpi_method = getattr(stats_repo, period.kpi_method, None)
            if not kpi_method:
                logger.error(f"[Достижения] Метод KPI {period.kpi_method} не найден")
                return stats

            # Получаем KPI данные для всех пользователей пакетом
            all_kpi_data = await _batch_get_kpi_data(
                kpi_method, stats_repo, playing_users
            )

            # Получаем всю историю достижений одним запросом
            existing_achievements = await _batch_get_achievement_history(
                stp_repo, playing_users, period.days_check
            )

            # Группируем достижения для быстрой проверки
            existing_by_user = _group_transactions_by_user(existing_achievements)

            # Обрабатываем всех пользователей с использованием предзагруженных данных
            all_earned = []
            for user in playing_users:
                try:
                    user_kpi = all_kpi_data.get(user.employee_id)
                    if not user_kpi:
                        continue

                    stats["users_processed"] += 1

                    # Проверяем достижения с использованием предзагруженных данных
                    earned = _check_user_achievements_fast(
                        user,
                        user_kpi,
                        achievements_index,
                        existing_by_user.get(user.user_id, set()),
                    )

                    if earned:
                        all_earned.append((user, earned))
                        stats["achievements_awarded"] += len(earned)

                except Exception as e:
                    stats["errors"] += 1
                    logger.error(
                        f"[Достижения] Ошибка {period.description} для {user.fullname}: {e}"
                    )
                    continue

            # Пакетное вручение достижений
            if all_earned:
                await _batch_award_achievements(stp_repo, all_earned, bot)

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


def _build_achievements_index(achievements: List) -> Dict:
    """Строит индекс достижений по критериям для быстрого поиска.

    Args:
        achievements: Список достижений

    Returns:
        Словарь {division: {position: [achievements]}}
    """
    index = {}
    for ach in achievements:
        if ach.division not in index:
            index[ach.division] = {}
        if ach.position not in index[ach.division]:
            index[ach.division][ach.position] = []
        index[ach.division][ach.position].append(ach)
    return index


async def _batch_get_kpi_data(
    kpi_method, stats_repo: StatsRequestsRepo, users: List
) -> Dict:
    """Пакетное получение KPI данных для всех пользователей.

    Args:
        kpi_method: Метод для получения KPI
        stats_repo: Репозиторий статистики
        users: Список пользователей

    Returns:
        Словарь {employee_id: {"kpi": user_kpi, "premium": user_premium, "extraction": extraction_date}}
    """
    result = {}
    employee_ids = [u.employee_id for u in users if u.employee_id]

    # Пакетное получение KPI данных
    for emp_id in employee_ids:
        try:
            user_kpi = await kpi_method.get_kpi(emp_id)
            if user_kpi and user_kpi.extraction_period:
                extraction_date = (
                    user_kpi.extraction_period.date()
                    if isinstance(user_kpi.extraction_period, datetime)
                    else user_kpi.extraction_period
                )

                # Получаем premium данные
                user_premium = await stats_repo.spec_premium.get_premium(
                    emp_id, extraction_date
                )

                result[emp_id] = {
                    "kpi": user_kpi,
                    "premium": user_premium,
                    "extraction": extraction_date,
                }
        except Exception as e:
            logger.debug(f"[Достижения] Ошибка получения KPI для {emp_id}: {e}")
            continue

    return result


async def _batch_get_achievement_history(
    stp_repo: MainRequestsRepo, users: List, days_check: int
) -> List[Transaction]:
    """Пакетное получение истории достижений для всех пользователей.

    Args:
        stp_repo: Репозиторий STP
        users: Список пользователей
        days_check: Количество дней для проверки

    Returns:
        Список всех транзакций достижений
    """
    try:
        cutoff_date = date.today() - timedelta(days=days_check)
        user_ids = [u.user_id for u in users if u.user_id]

        if not user_ids:
            return []

        # Один запрос для всех пользователей
        query = select(Transaction).filter(
            and_(
                Transaction.user_id.in_(user_ids),
                Transaction.source_type == "achievement",
                func.date(Transaction.created_at) >= cutoff_date,
            )
        )
        result = await stp_repo.session.execute(query)
        return result.scalars().all()

    except Exception as e:
        logger.error(f"[Достижения] Ошибка пакетного получения истории: {e}")
        return []


def _group_transactions_by_user(transactions: List[Transaction]) -> Dict[int, set]:
    """Группирует транзакции по пользователям для быстрого поиска.

    Args:
        transactions: Список транзакций

    Returns:
        Словарь {user_id: set(source_ids)}
    """
    grouped = {}
    for txn in transactions:
        if txn.user_id not in grouped:
            grouped[txn.user_id] = set()
        if txn.source_id:
            grouped[txn.user_id].add(txn.source_id)
    return grouped


def _check_user_achievements_fast(
    user,
    user_kpi_data: Dict,
    achievements_index: Dict,
    existing_achievement_ids: set,
) -> List[Dict]:
    """Быстрая проверка достижений для пользователя с использованием индекса.

    Args:
        user: Пользователь
        user_kpi_data: Данные KPI пользователя
        achievements_index: Индекс достижений
        existing_achievement_ids: Множество уже полученных достижений

    Returns:
        Список заработанных достижений
    """
    if not user.user_id:
        return []

    earned = []
    user_kpi = user_kpi_data["kpi"]
    user_premium = user_kpi_data["premium"]

    # Получаем подходящие достижения из индекса
    matching_division = achievements_index.get(user.division, {})
    all_position = matching_division.get("ALL", [])
    specific_position = matching_division.get(user.position, [])
    applicable_achievements = all_position + specific_position

    # Добавляем достижения для "ALL" division
    if "ALL" in achievements_index:
        all_div_all_pos = achievements_index["ALL"].get("ALL", [])
        all_div_spec_pos = achievements_index["ALL"].get(user.position, [])
        applicable_achievements.extend(all_div_all_pos + all_div_spec_pos)

    # Проверяем каждое достижение
    for ach in applicable_achievements:
        try:
            if ach.id in existing_achievement_ids:
                continue

            if not _user_matches_achievement_criteria(user, ach):
                continue

            if _check_kpi_criteria_sync(user_kpi, ach.kpi, user_premium):
                earned.append({
                    "id": ach.id,
                    "name": ach.name,
                    "description": ach.description,
                    "reward_points": ach.reward,
                    "kpi_values": _get_user_kpi_values(user_kpi, ach.kpi, user_premium),
                    "extraction_period": user_kpi_data["extraction"],
                })
                logger.info(f"[Достижения] {user.fullname} заработал '{ach.name}'")

        except Exception as e:
            logger.error(f"[Достижения] Ошибка проверки {ach.name}: {e}")
            continue

    return earned


def _check_kpi_criteria_sync(
    user_kpi, kpi_criteria_str: str, user_premium=None
) -> bool:
    """Синхронная проверка KPI критериев.

    Args:
        user_kpi: KPI пользователя
        kpi_criteria_str: JSON строка с критериями
        user_premium: Premium данные

    Returns:
        True если соответствует критериям
    """
    try:
        kpi_criteria = json.loads(kpi_criteria_str)

        for kpi_name, criteria_range in kpi_criteria.items():
            min_val, max_val = criteria_range[0], criteria_range[1]
            user_value = _get_kpi_value(user_kpi, kpi_name, user_premium)

            if user_value is None or not (min_val <= user_value <= max_val):
                return False

        return True

    except Exception:
        return False


async def _batch_award_achievements(
    stp_repo: MainRequestsRepo, all_earned: List, bot: Bot
) -> None:
    """Пакетное вручение достижений с группировкой по пользователям.

    Args:
        stp_repo: Репозиторий STP
        all_earned: Список (user, achievements) для вручения
        bot: Экземпляр бота
    """
    try:
        # Готовим все транзакции для bulk insert
        all_transactions_data = []
        achievements_by_txn = {}  # Ссылка на данные достижения для логов

        for user, achievements in all_earned:
            for achievement in achievements:
                txn_data = {
                    "user_id": user.user_id,
                    "type": "earn",
                    "source_type": "achievement",
                    "amount": achievement["reward_points"],
                    "source_id": achievement["id"],
                    "comment": f'Достижение "{achievement["name"]}". Показатель: {_format_kpi_values(achievement["kpi_values"])}',
                    "kpi_extracted_at": achievement.get("extraction_period"),
                }
                all_transactions_data.append(txn_data)
                achievements_by_txn[(user.user_id, achievement["id"])] = (
                    user,
                    achievement,
                )

        # Bulk insert всех транзакций одной операцией
        if all_transactions_data:
            created_transactions = await _bulk_insert_transactions(
                stp_repo, all_transactions_data
            )

            # Группируем успешно созданные транзакции по пользователям
            successful_by_user = {}
            for txn in created_transactions:
                key = (txn.user_id, txn.source_id)
                if key in achievements_by_txn:
                    user, achievement = achievements_by_txn[key]
                    if user not in successful_by_user:
                        successful_by_user[user] = []
                    successful_by_user[user].append((txn, achievement))

            # Вычисляем финальные балансы и отправляем уведомления
            for user, user_txns in successful_by_user.items():
                total_reward = sum(txn.amount for txn, _ in user_txns)
                final_balance = await stp_repo.transaction.get_user_balance(
                    user.user_id
                )

                # Подготавливаем данные для уведомления
                achievements_for_notification = []
                for _, achievement in user_txns:
                    achievements_for_notification.append({
                        "id": achievement["id"],
                        "name": achievement["name"],
                        "description": achievement["description"],
                        "reward_points": achievement["reward_points"],
                        "kpi_values": achievement["kpi_values"],
                    })

                message = _create_batch_achievements_message(
                    achievements_for_notification, total_reward, final_balance
                )
                await send_message(bot, user.user_id, message)

                logger.info(
                    f"[Достижения] Вручено {len(user_txns)} достижений пользователю {user.fullname}"
                )

    except Exception as e:
        logger.error(f"[Достижения] Ошибка пакетного вручения: {e}")


async def _bulk_insert_transactions(
    stp_repo: MainRequestsRepo, transactions_data: List[Dict]
) -> List[Transaction]:
    """Создает множество транзакций одной bulk операцией.

    Args:
        stp_repo: Репозиторий STP
        transactions_data: Список словарей с данными транзакций

    Returns:
        Список созданных транзакций
    """
    try:
        session = stp_repo.session

        # Создаем объекты Transaction
        transactions = [
            Transaction(
                user_id=data["user_id"],
                type=data["type"],
                source_type=data["source_type"],
                amount=data["amount"],
                source_id=data["source_id"],
                comment=data.get("comment"),
                kpi_extracted_at=data.get("kpi_extracted_at"),
            )
            for data in transactions_data
        ]

        # Добавляем все в сессию
        session.add_all(transactions)

        # Коммитим одной транзакцией
        await session.commit()

        # Refresh для получения ID
        for txn in transactions:
            await session.refresh(txn)

        logger.info(f"[БД] Создано {len(transactions)} транзакций bulk операцией")

        return transactions

    except Exception as e:
        logger.error(f"[БД] Ошибка bulk вставки транзакций: {e}")
        await stp_repo.session.rollback()
        return []


# ========== Вспомогательные функции для проверки и форматирования ==========


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
