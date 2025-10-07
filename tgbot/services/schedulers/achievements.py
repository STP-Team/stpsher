"""Планировщик достижений и наград

Содержит задачи по проверке и вручению достижений пользователям,
обработке игровых механик и периодических наград.
"""

import json
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Sequence

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import and_, func, select

from infrastructure.database.models.STP.transactions import Transaction
from infrastructure.database.repo.KPI.requests import KPIRequestsRepo
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.services.broadcaster import send_message
from tgbot.services.schedulers.base import BaseScheduler

logger = logging.getLogger(__name__)


class AchievementScheduler(BaseScheduler):
    """Планировщик достижений и наград

    Управляет задачами связанными с игровыми механиками:
    - Проверка новых достижений
    - Вручение периодических наград
    - Обновление игровой статистики
    - Уведомления о достижениях
    """

    def __init__(self):
        super().__init__("Достижения")

    def setup_jobs(
        self, scheduler: AsyncIOScheduler, session_pool, bot: Bot, kpi_session_pool=None
    ):
        """Настройка всех задач достижений"""
        self.logger.info("Настройка задач достижений...")

        # Проверка ежедневных достижений - раз в 12 часов, запускать при старте
        scheduler.add_job(
            func=self._check_daily_achievements_job,
            args=[session_pool, kpi_session_pool, bot],
            trigger="interval",
            id="achievements_check_daily_achievements",
            name="Проверка ежедневных достижений",
            hours=12,
            coalesce=True,
            misfire_grace_time=300,
            replace_existing=True,
        )

        # Проверка еженедельных достижений - раз в 12 часов, запускать при старте
        scheduler.add_job(
            func=self._check_weekly_achievements_job,
            args=[session_pool, kpi_session_pool, bot],
            trigger="interval",
            id="achievements_check_weekly_achievements",
            name="Проверка еженедельных достижений",
            hours=12,
            coalesce=True,
            misfire_grace_time=300,
            replace_existing=True,
        )

        # Проверка ежемесячных достижений - раз в 12 часов, запускать при старте
        scheduler.add_job(
            func=self._check_monthly_achievements_job,
            args=[session_pool, kpi_session_pool, bot],
            trigger="interval",
            id="achievements_check_monthly_achievements",
            name="Проверка ежемесячных достижений",
            hours=12,
            coalesce=True,
            misfire_grace_time=300,
            replace_existing=True,
        )

        # Запуск задач при старте
        scheduler.add_job(
            func=self._check_daily_achievements_job,
            args=[session_pool, kpi_session_pool, bot],
            trigger="date",
            id="achievements_startup_daily_achievements",
            name="Запуск при старте: Проверка ежедневных достижений",
            run_date=None,
        )

        scheduler.add_job(
            func=self._check_weekly_achievements_job,
            args=[session_pool, kpi_session_pool, bot],
            trigger="date",
            id="achievements_startup_weekly_achievements",
            name="Запуск при старте: Проверка еженедельных достижений",
            run_date=None,
        )

        scheduler.add_job(
            func=self._check_monthly_achievements_job,
            args=[session_pool, kpi_session_pool, bot],
            trigger="date",
            id="achievements_startup_monthly_achievements",
            name="Запуск при старте: Проверка ежемесячных достижений",
            run_date=None,
        )

    async def _check_daily_achievements_job(
        self, session_pool, kpi_session_pool, bot: Bot
    ):
        """Проверка ежедневных достижений"""
        self._log_job_execution_start("Ежедневная проверка достижений")
        try:
            await check_daily_achievements(session_pool, kpi_session_pool, bot)
            self._log_job_execution_end("Ежедневная проверка достижений", success=True)
        except Exception as e:
            self._log_job_execution_end(
                "Ежедневная проверка достижений", success=False, error=str(e)
            )

    async def _check_weekly_achievements_job(
        self, session_pool, kpi_session_pool, bot: Bot
    ):
        """Проверка еженедельных достижений"""
        self._log_job_execution_start("Еженедельная проверка достижений")
        try:
            await check_weekly_achievements(session_pool, kpi_session_pool, bot)
            self._log_job_execution_end(
                "Еженедельная проверка достижений", success=True
            )
        except Exception as e:
            self._log_job_execution_end(
                "Еженедельная проверка достижений", success=False, error=str(e)
            )

    async def _check_monthly_achievements_job(
        self, session_pool, kpi_session_pool, bot: Bot
    ):
        """Проверка ежемесячных достижений"""
        self._log_job_execution_start("Ежемесячная проверка достижений")
        try:
            await check_monthly_achievements(session_pool, kpi_session_pool, bot)
            self._log_job_execution_end("Ежемесячная проверка достижений", success=True)
        except Exception as e:
            self._log_job_execution_end(
                "Ежемесячная проверка достижений", success=False, error=str(e)
            )


# Функции для работы с достижениями
async def check_daily_achievements(session_pool, kpi_session_pool, bot: Bot):
    """Проверка и вручение ежедневных достижений

    Args:
        session_pool: Пул сессий основной БД
        kpi_session_pool: Пул сессий KPI БД
        bot: Экземпляр бота
    """
    try:
        async with session_pool() as stp_session, kpi_session_pool() as kpi_session:
            stp_repo = MainRequestsRepo(stp_session)
            kpi_repo = KPIRequestsRepo(kpi_session)

            # Получаем всех пользователей
            playing_users = await stp_repo.employee.get_users(roles=[1, 3, 10])

            if not playing_users:
                logger.info("[Достижения] Нет пользователей в базе данных")
                return

            # Получаем все ежедневные достижения
            daily_achievements_list = await stp_repo.achievement.get_achievements()
            daily_achievements_list = [
                ach for ach in daily_achievements_list if ach.period == "d"
            ]

            if not daily_achievements_list:
                logger.info("[Достижения] Нет ежедневных достижений в базе данных")
                return

            logger.info(
                f"[Достижения] Проверка {len(daily_achievements_list)} ежедневных достижений для {len(playing_users)} пользователей"
            )

            new_achievements_count = 0

            for user in playing_users:
                try:
                    # Проверяем достижения для пользователя
                    earned_achievements = await _check_user_daily_achievements(
                        stp_repo, kpi_repo, user, daily_achievements_list
                    )

                    if earned_achievements:
                        await _award_achievements(
                            stp_repo, user, earned_achievements, bot
                        )
                        new_achievements_count += len(earned_achievements)

                except Exception as e:
                    logger.error(
                        f"[Достижения] Ошибка проверки достижений для пользователя {user.fullname}: {e}"
                    )
                    continue

            logger.info(
                f"[Достижения] Вручено {new_achievements_count} ежедневных достижений"
            )

    except Exception as e:
        logger.error(
            f"[Достижения] Критическая ошибка при проверке ежедневных достижений: {e}"
        )


async def check_weekly_achievements(session_pool, kpi_session_pool, bot: Bot):
    """Проверка и вручение еженедельных достижений

    Args:
        session_pool: Пул сессий основной БД
        kpi_session_pool: Пул сессий KPI БД
        bot: Экземпляр бота
    """
    try:
        async with session_pool() as stp_session, kpi_session_pool() as kpi_session:
            stp_repo = MainRequestsRepo(stp_session)
            kpi_repo = KPIRequestsRepo(kpi_session)

            # Получаем всех пользователей
            playing_users = await stp_repo.employee.get_users(roles=[1, 3, 10])

            if not playing_users:
                logger.info("[Достижения] Нет пользователей в базе данных")
                return

            # Получаем все еженедельные достижения
            weekly_achievements_list = await stp_repo.achievement.get_achievements()
            weekly_achievements_list = [
                ach for ach in weekly_achievements_list if ach.period == "w"
            ]

            if not weekly_achievements_list:
                logger.info("[Достижения] Нет еженедельных достижений в базе данных")
                return

            logger.info(
                f"[Достижения] Проверка {len(weekly_achievements_list)} еженедельных достижений для {len(playing_users)} пользователей"
            )

            new_achievements_count = 0

            for user in playing_users:
                try:
                    # Проверяем достижения для пользователя
                    earned_achievements = await _check_user_weekly_achievements(
                        stp_repo, kpi_repo, user, weekly_achievements_list
                    )

                    if earned_achievements:
                        await _award_achievements(
                            stp_repo, user, earned_achievements, bot
                        )
                        new_achievements_count += len(earned_achievements)

                except Exception as e:
                    logger.error(
                        f"[Достижения] Ошибка проверки еженедельных достижений для пользователя {user.fullname}: {e}"
                    )
                    continue

            logger.info(
                f"[Достижения] Вручено {new_achievements_count} еженедельных достижений"
            )

    except Exception as e:
        logger.error(
            f"[Достижения] Критическая ошибка при проверке еженедельных достижений: {e}"
        )


async def check_monthly_achievements(session_pool, kpi_session_pool, bot: Bot):
    """Проверка и вручение ежемесячных достижений

    Args:
        session_pool: Пул сессий основной БД
        kpi_session_pool: Пул сессий KPI БД
        bot: Экземпляр бота
    """
    try:
        async with session_pool() as stp_session, kpi_session_pool() as kpi_session:
            stp_repo = MainRequestsRepo(stp_session)
            kpi_repo = KPIRequestsRepo(kpi_session)

            # Получаем всех пользователей
            playing_users = await stp_repo.employee.get_users(roles=[1, 3, 10])

            if not playing_users:
                logger.info("[Достижения] Нет пользователей в базе данных")
                return

            # Получаем все ежемесячные достижения
            monthly_achievements_list = await stp_repo.achievement.get_achievements()
            monthly_achievements_list = [
                ach for ach in monthly_achievements_list if ach.period == "m"
            ]

            if not monthly_achievements_list:
                logger.info("[Достижения] Нет ежемесячных достижений в базе данных")
                return

            logger.info(
                f"[Достижения] Проверка {len(monthly_achievements_list)} ежемесячных достижений для {len(playing_users)} пользователей"
            )

            new_achievements_count = 0

            for user in playing_users:
                try:
                    # Проверяем достижения для пользователя
                    earned_achievements = await _check_user_monthly_achievements(
                        stp_repo, kpi_repo, user, monthly_achievements_list
                    )

                    if earned_achievements:
                        await _award_achievements(
                            stp_repo, user, earned_achievements, bot
                        )
                        new_achievements_count += len(earned_achievements)

                except Exception as e:
                    logger.error(
                        f"[Достижения] Ошибка проверки ежемесячных достижений для пользователя {user.fullname}: {e}"
                    )
                    continue

            logger.info(
                f"[Достижения] Вручено {new_achievements_count} ежемесячных достижений"
            )

    except Exception as e:
        logger.error(
            f"[Достижения] Критическая ошибка при проверке ежемесячных достижений: {e}"
        )


# Вспомогательные функции
async def _check_user_daily_achievements(
    stp_repo: MainRequestsRepo, kpi_repo: KPIRequestsRepo, user, achievements_list: List
) -> List[Dict]:
    """Проверка ежедневных достижений для конкретного пользователя

    Args:
        stp_repo: Репозиторий основной БД
        kpi_repo: Репозиторий KPI БД
        user: Пользователь
        achievements_list: Список доступных ежедневных достижений

    Returns:
        Список новых достижений для вручения
    """
    earned_achievements = []

    try:
        if not user.user_id:
            return earned_achievements

        # Получаем KPI пользователя за сегодня
        user_kpi = await kpi_repo.spec_day_kpi.get_kpi(user.fullname)
        if not user_kpi:
            logger.debug(
                f"[Достижения] Нет KPI данных для пользователя {user.fullname}"
            )
            return earned_achievements

        # Получаем kpi_extract_date из KPI данных
        kpi_extract_date = user_kpi.kpi_extract_date
        if not kpi_extract_date:
            logger.debug(
                f"[Достижения] Нет kpi_extract_date в KPI данных для пользователя {user.fullname}"
            )
            return earned_achievements

        # Проверяем, есть ли уже достижения с этим kpi_extracted_at
        existing_transactions = await _get_user_achievements_by_kpi_date(
            stp_repo, user.user_id, kpi_extract_date
        )
        existing_achievement_ids = {
            t.source_id for t in existing_transactions if t.source_id
        }

        # Также проверяем достижения за последний день (для предотвращения дублирования)
        recent_transactions = await _get_user_achievements_last_n_days(
            stp_repo, user.user_id, 1
        )
        recent_achievement_ids = {
            t.source_id for t in recent_transactions if t.source_id
        }

        # Проверяем каждое доступное достижение
        for achievement in achievements_list:
            try:
                # Пропускаем достижение если уже получено с этим kpi_extracted_at
                if achievement.id in existing_achievement_ids:
                    logger.debug(
                        f"[Достижения] Достижение {achievement.name} уже получено для kpi_extract_date {kpi_extract_date}"
                    )
                    continue

                # Пропускаем если достижение было получено за последний день
                if achievement.id in recent_achievement_ids:
                    logger.debug(
                        f"[Достижения] Достижение {achievement.name} уже получено за последний день"
                    )
                    continue

                # Проверяем соответствие пользователя критериям достижения
                if not _user_matches_achievement_criteria(user, achievement):
                    continue

                # Проверяем KPI критерии
                if await _check_kpi_criteria(user_kpi, achievement.kpi):
                    earned_achievements.append({
                        "id": achievement.id,
                        "name": achievement.name,
                        "description": achievement.description,
                        "reward_points": achievement.reward,
                        "kpi_values": _get_user_kpi_values(user_kpi, achievement.kpi),
                        "kpi_extract_date": kpi_extract_date,  # Добавляем дату KPI
                    })
                    logger.info(
                        f"[Достижения] Пользователь {user.fullname} заработал достижение '{achievement.name}'"
                    )

            except Exception as e:
                logger.error(
                    f"[Достижения] Ошибка проверки достижения {achievement.name} для {user.fullname}: {e}"
                )
                continue

    except Exception as e:
        logger.error(
            f"[Достижения] Ошибка проверки достижений пользователя {user.fullname}: {e}"
        )

    return earned_achievements


async def _check_user_weekly_achievements(
    stp_repo: MainRequestsRepo, kpi_repo: KPIRequestsRepo, user, achievements_list: List
) -> List[Dict]:
    """Проверка еженедельных достижений для конкретного пользователя

    Args:
        stp_repo: Репозиторий основной БД
        kpi_repo: Репозиторий KPI БД
        user: Пользователь
        achievements_list: Список доступных еженедельных достижений

    Returns:
        Список новых достижений для вручения
    """
    earned_achievements = []

    try:
        if not user.user_id:
            return earned_achievements

        # Получаем KPI пользователя за неделю
        user_kpi = await kpi_repo.spec_week_kpi.get_kpi(user.fullname)
        if not user_kpi:
            logger.debug(
                f"[Достижения] Нет недельных KPI данных для пользователя {user.fullname}"
            )
            return earned_achievements

        # Получаем kpi_extract_date из KPI данных
        kpi_extract_date = user_kpi.kpi_extract_date
        if not kpi_extract_date:
            logger.debug(
                f"[Достижения] Нет kpi_extract_date в недельных KPI данных для пользователя {user.fullname}"
            )
            return earned_achievements

        # Проверяем, есть ли уже достижения с этим kpi_extracted_at
        existing_transactions = await _get_user_achievements_by_kpi_date(
            stp_repo, user.user_id, kpi_extract_date
        )
        existing_achievement_ids = {
            t.source_id for t in existing_transactions if t.source_id
        }

        # Также проверяем достижения за последнюю неделю (для предотвращения дублирования)
        recent_transactions = await _get_user_achievements_last_n_days(
            stp_repo, user.user_id, 7
        )
        recent_achievement_ids = {
            t.source_id for t in recent_transactions if t.source_id
        }

        # Проверяем каждое доступное достижение
        for achievement in achievements_list:
            try:
                # Пропускаем достижение если уже получено с этим kpi_extracted_at
                if achievement.id in existing_achievement_ids:
                    logger.debug(
                        f"[Достижения] Достижение {achievement.name} уже получено для kpi_extract_date {kpi_extract_date}"
                    )
                    continue

                # Пропускаем если достижение было получено за последнюю неделю
                if achievement.id in recent_achievement_ids:
                    logger.debug(
                        f"[Достижения] Достижение {achievement.name} уже получено за последнюю неделю"
                    )
                    continue

                # Проверяем соответствие пользователя критериям достижения
                if not _user_matches_achievement_criteria(user, achievement):
                    continue

                # Проверяем KPI критерии
                if await _check_kpi_criteria(user_kpi, achievement.kpi):
                    earned_achievements.append({
                        "id": achievement.id,
                        "name": achievement.name,
                        "description": achievement.description,
                        "reward_points": achievement.reward,
                        "kpi_values": _get_user_kpi_values(user_kpi, achievement.kpi),
                        "kpi_extract_date": kpi_extract_date,  # Добавляем дату KPI
                    })
                    logger.info(
                        f"[Достижения] Пользователь {user.fullname} заработал еженедельное достижение '{achievement.name}'"
                    )

            except Exception as e:
                logger.error(
                    f"[Достижения] Ошибка проверки еженедельного достижения {achievement.name} для {user.fullname}: {e}"
                )
                continue

    except Exception as e:
        logger.error(
            f"[Достижения] Ошибка проверки еженедельных достижений пользователя {user.fullname}: {e}"
        )

    return earned_achievements


async def _check_user_monthly_achievements(
    stp_repo: MainRequestsRepo, kpi_repo: KPIRequestsRepo, user, achievements_list: List
) -> List[Dict]:
    """Проверка ежемесячных достижений для конкретного пользователя

    Args:
        stp_repo: Репозиторий основной БД
        kpi_repo: Репозиторий KPI БД
        user: Пользователь
        achievements_list: Список доступных ежемесячных достижений

    Returns:
        Список новых достижений для вручения
    """
    earned_achievements = []

    try:
        if not user.user_id:
            return earned_achievements

        # Получаем KPI пользователя за месяц
        user_kpi = await kpi_repo.spec_month_kpi.get_kpi(user.fullname)
        if not user_kpi:
            logger.debug(
                f"[Достижения] Нет месячных KPI данных для пользователя {user.fullname}"
            )
            return earned_achievements

        # Получаем kpi_extract_date из KPI данных
        kpi_extract_date = user_kpi.kpi_extract_date
        if not kpi_extract_date:
            logger.debug(
                f"[Достижения] Нет kpi_extract_date в месячных KPI данных для пользователя {user.fullname}"
            )
            return earned_achievements

        # Проверяем, есть ли уже достижения с этим kpi_extracted_at
        existing_transactions = await _get_user_achievements_by_kpi_date(
            stp_repo, user.user_id, kpi_extract_date
        )
        existing_achievement_ids = {
            t.source_id for t in existing_transactions if t.source_id
        }

        # Также проверяем достижения за последний месяц (для предотвращения дублирования)
        recent_transactions = await _get_user_achievements_last_n_days(
            stp_repo, user.user_id, 30
        )
        recent_achievement_ids = {
            t.source_id for t in recent_transactions if t.source_id
        }

        # Проверяем каждое доступное достижение
        for achievement in achievements_list:
            try:
                # Пропускаем достижение если уже получено с этим kpi_extracted_at
                if achievement.id in existing_achievement_ids:
                    logger.debug(
                        f"[Достижения] Достижение {achievement.name} уже получено для kpi_extract_date {kpi_extract_date}"
                    )
                    continue

                # Пропускаем если достижение было получено за последний месяц
                if achievement.id in recent_achievement_ids:
                    logger.debug(
                        f"[Достижения] Достижение {achievement.name} уже получено за последний месяц"
                    )
                    continue

                # Проверяем соответствие пользователя критериям достижения
                if not _user_matches_achievement_criteria(user, achievement):
                    continue

                # Проверяем KPI критерии
                if await _check_kpi_criteria(user_kpi, achievement.kpi):
                    earned_achievements.append({
                        "id": achievement.id,
                        "name": achievement.name,
                        "description": achievement.description,
                        "reward_points": achievement.reward,
                        "kpi_values": _get_user_kpi_values(user_kpi, achievement.kpi),
                        "kpi_extract_date": kpi_extract_date,  # Добавляем дату KPI
                    })
                    logger.info(
                        f"[Достижения] Пользователь {user.fullname} заработал ежемесячное достижение '{achievement.name}'"
                    )

            except Exception as e:
                logger.error(
                    f"[Достижения] Ошибка проверки ежемесячного достижения {achievement.name} для {user.fullname}: {e}"
                )
                continue

    except Exception as e:
        logger.error(
            f"[Достижения] Ошибка проверки ежемесячных достижений пользователя {user.fullname}: {e}"
        )

    return earned_achievements


async def _award_achievements(
    stp_repo: MainRequestsRepo, user, achievements: List[Dict], bot: Bot
):
    """Вручение достижений пользователю

    Args:
        stp_repo: Репозиторий БД
        user: Пользователь
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
                kpi_extracted_at=achievement.get("kpi_extract_date"),
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


async def _get_user_achievements_today(
    stp_repo: MainRequestsRepo, user_id: int
) -> Sequence[Transaction] | list[Any]:
    """Получает достижения пользователя за сегодня

    Args:
        stp_repo: Репозиторий БД
        user_id: ID пользователя

    Returns:
        Список транзакций-достижений за сегодня
    """
    try:
        today = date.today()

        # Получаем транзакции-достижения за сегодня
        query = select(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.source_type == "achievement",
                func.date(Transaction.created_at) == today,
            )
        )

        result = await stp_repo.session.execute(query)
        return result.scalars().all()

    except Exception as e:
        logger.error(
            f"[Достижения] Ошибка получения достижений сегодня для пользователя {user_id}: {e}"
        )
        return []


async def _get_user_achievements_this_week(
    stp_repo: MainRequestsRepo, user_id: int
) -> Sequence[Transaction] | list[Any]:
    """Получает достижения пользователя за текущую неделю

    Args:
        stp_repo: Репозиторий БД
        user_id: ID пользователя

    Returns:
        Список транзакций-достижений за текущую неделю
    """
    try:
        # Вычисляем начало недели (понедельник)
        today = date.today()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)

        # Получаем транзакции-достижения за текущую неделю
        query = select(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.source_type == "achievement",
                func.date(Transaction.created_at) >= week_start,
            )
        )

        result = await stp_repo.session.execute(query)
        return result.scalars().all()

    except Exception as e:
        logger.error(
            f"[Достижения] Ошибка получения достижений на этой неделе для пользователя {user_id}: {e}"
        )
        return []


async def _get_user_achievements_this_month(
    stp_repo: MainRequestsRepo, user_id: int
) -> Sequence[Transaction] | list[Any]:
    """Получает достижения пользователя за текущий месяц

    Args:
        stp_repo: Репозиторий БД
        user_id: ID пользователя

    Returns:
        Список транзакций-достижений за текущий месяц
    """
    try:
        # Вычисляем начало месяца
        today = date.today()
        month_start = today.replace(day=1)

        # Получаем транзакции-достижения за текущий месяц
        query = select(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.source_type == "achievement",
                func.date(Transaction.created_at) >= month_start,
            )
        )

        result = await stp_repo.session.execute(query)
        return result.scalars().all()

    except Exception as e:
        logger.error(
            f"[Достижения] Ошибка получения достижений в этом месяце для пользователя {user_id}: {e}"
        )
        return []


async def _get_user_achievements_by_kpi_date(
    stp_repo: MainRequestsRepo, user_id: int, kpi_extract_date
) -> Sequence[Transaction] | list:
    """Получает достижения пользователя с определенным kpi_extracted_at

    Args:
        stp_repo: Репозиторий БД
        user_id: ID пользователя
        kpi_extract_date: Дата извлечения KPI

    Returns:
        Список транзакций-достижений с указанным kpi_extracted_at
    """
    try:
        # Получаем транзакции-достижения с указанным kpi_extracted_at
        query = select(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.source_type == "achievement",
                Transaction.kpi_extracted_at == kpi_extract_date,
            )
        )

        result = await stp_repo.session.execute(query)
        return result.scalars().all()

    except Exception as e:
        logger.error(
            f"[Достижения] Ошибка получения достижений по kpi_extract_date {kpi_extract_date} для пользователя {user_id}: {e}"
        )
        return []


async def _get_user_achievements_last_n_days(
    stp_repo: MainRequestsRepo, user_id: int, n_days: int
) -> Sequence[Transaction] | list:
    """Получает достижения пользователя за последние n дней

    Args:
        stp_repo: Репозиторий БД
        user_id: ID пользователя
        n_days: Количество дней назад

    Returns:
        Список транзакций-достижений за последние n дней
    """
    try:
        # Вычисляем дату n дней назад
        cutoff_date = date.today() - timedelta(days=n_days)

        # Получаем транзакции-достижения за последние n дней
        query = select(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.source_type == "achievement",
                func.date(Transaction.created_at) >= cutoff_date,
            )
        )

        result = await stp_repo.session.execute(query)
        return result.scalars().all()

    except Exception as e:
        logger.error(
            f"[Достижения] Ошибка получения достижений за последние {n_days} дней для пользователя {user_id}: {e}"
        )
        return []


def _user_matches_achievement_criteria(user, achievement) -> bool:
    """Проверяет соответствие пользователя критериям достижения

    Args:
        user: Пользователь
        achievement: Достижение

    Returns:
        True если пользователь подходит под критерии
    """
    try:
        # Проверяем направление (division)
        if achievement.division != "ALL":
            user_division = user.division
            achievement_division = achievement.division

            # Если достижение для НЦК - пользователь должен быть только из НЦК
            if achievement_division == "НЦК":
                if user_division != "НЦК":
                    return False
            # Если достижение для НТП - пользователь может быть из НТП, НТП1, НТП2
            elif achievement_division == "НТП":
                if user_division not in ["НТП", "НТП1", "НТП2"]:
                    return False
            # Для других направлений - точное совпадение
            else:
                if user_division != achievement_division:
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


async def _check_kpi_criteria(user_kpi, kpi_criteria_str: str) -> bool:
    """Проверяет соответствие KPI пользователя критериям достижения

    Args:
        user_kpi: KPI пользователя за день
        kpi_criteria_str: JSON строка с критериями (например: {"AHT":[0,740],"CC":[20,99999]})

    Returns:
        True если KPI соответствует критериям
    """
    try:
        kpi_criteria = json.loads(kpi_criteria_str)

        for kpi_name, criteria_range in kpi_criteria.items():
            min_val, max_val = criteria_range[0], criteria_range[1]

            # Получаем значение KPI пользователя
            user_value = None

            if kpi_name == "AHT":
                user_value = user_kpi.aht
            elif kpi_name == "CC" or kpi_name == "TC":  # TC - это contacts_count
                user_value = user_kpi.contacts_count
            elif kpi_name == "FLR":
                user_value = user_kpi.flr
            elif kpi_name == "CSI":
                user_value = user_kpi.csi
            elif kpi_name == "POK":
                user_value = user_kpi.pok
            elif kpi_name == "DELAY":
                user_value = user_kpi.delay
            elif kpi_name == "SalesCount":
                user_value = user_kpi.sales_count
            elif kpi_name == "SalesPotential":
                user_value = user_kpi.sales_potential

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


def _get_user_kpi_values(user_kpi, kpi_criteria_str: str) -> Dict:
    """Получает актуальные значения KPI пользователя согласно критериям

    Args:
        user_kpi: KPI пользователя за день
        kpi_criteria_str: JSON строка с критериями

    Returns:
        Словарь с актуальными значениями KPI
    """
    kpi_values = {}

    try:
        kpi_criteria = json.loads(kpi_criteria_str)

        for kpi_name in kpi_criteria.keys():
            if kpi_name == "AHT":
                kpi_values["AHT"] = user_kpi.aht
            elif kpi_name == "CC" or kpi_name == "TC":
                kpi_values["Контактов"] = user_kpi.contacts_count
            elif kpi_name == "FLR":
                kpi_values["FLR"] = user_kpi.flr
            elif kpi_name == "CSI":
                kpi_values["CSI"] = user_kpi.csi
            elif kpi_name == "POK":
                kpi_values["POK"] = user_kpi.pok
            elif kpi_name == "DELAY":
                kpi_values["DELAY"] = user_kpi.delay
            elif kpi_name == "SalesCount":
                kpi_values["SalesCount"] = user_kpi.sales_count
            elif kpi_name == "SalesPotential":
                kpi_values["SalesPotential"] = user_kpi.sales_potential

    except Exception as e:
        logger.error(f"[Достижения] Ошибка получения значений KPI: {e}")

    return kpi_values


def _format_kpi_values(kpi_values: Dict) -> str:
    """Форматирует KPI значения в читаемую строку

    Args:
        kpi_values: Словарь с KPI значениями

    Returns:
        Отформатированная строка
    """
    kpi_parts = []
    for kpi_name, value in kpi_values.items():
        if value is not None:
            kpi_parts.append(f"{kpi_name} {value}")
    return ", ".join(kpi_parts)


def _create_achievement_message(achievement: Dict, new_balance: int = None) -> str:
    """Создание сообщения о получении достижения

    Args:
        achievement: Данные о достижении
        new_balance: Новый баланс пользователя

    Returns:
        Текст сообщения
    """
    message_parts = [
        "🏆 <b>Новое достижение!</b>\n",
        f"🎉 <b>{achievement['name']}: {achievement['reward_points']} балла за {achievement['description']}</b>\n",
    ]

    # Показываем KPI показатели
    if achievement.get("kpi_values"):
        formatted_kpi = _format_kpi_values(achievement["kpi_values"])
        if formatted_kpi:
            message_parts.append(f"Твои показатели: {formatted_kpi}")

    if new_balance is not None:
        message_parts.append(f"Новый баланс: {new_balance} баллов")

    message_parts.append("\n✨  Поздравляем с новым достижением!")

    return "\n".join(message_parts)


def _create_batch_achievements_message(
    achievements: List[Dict], total_reward: int, final_balance: int = None
) -> str:
    """Создание сообщения о получении нескольких достижений

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

        # Показываем KPI показатели
        if achievement.get("kpi_values"):
            formatted_kpi = _format_kpi_values(achievement["kpi_values"])
            if formatted_kpi:
                message_parts.append(f"   📊 Твои показатели: {formatted_kpi}")

        message_parts.append("")  # Пустая строка между достижениями

    message_parts.append(f"💰 <b>Общая награда: {total_reward} баллов</b>")

    if final_balance is not None:
        message_parts.append(f"💎 Текущий баланс: {final_balance} баллов")

    message_parts.append("\n✨ Поздравляем с новыми достижениями!")

    return "\n".join(message_parts)
