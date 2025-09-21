import logging
from typing import Sequence

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.services.leveling import LevelingSystem

logger = logging.getLogger(__name__)

# Константы для пагинации
USERS_PER_PAGE = 10


class SearchService:
    """Универсальный сервис поиска сотрудников"""

    @staticmethod
    def filter_users_by_type(
        users: Sequence[Employee], search_type: str
    ) -> list[Employee]:
        """
        Фильтрация пользователей по типу поиска

        :param users: Список пользователей
        :param search_type: Тип поиска (specialists, heads, all)
        :return: Отфильтрованный список пользователей
        """
        if search_type == "specialists":
            # Специалисты - роль 1 (обычные пользователи)
            return [user for user in users if user.role == 1]
        elif search_type == "heads":
            # Руководители - роль 2 (руководители)
            return [user for user in users if user.role == 2]
        else:
            # Все пользователи
            return list(users)

    @staticmethod
    async def get_user_statistics(user_id: int, stp_repo: MainRequestsRepo) -> dict:
        """Получить статистику пользователя (уровень, очки, достижения, покупки)"""
        try:
            # Получаем базовые данные
            user_purchases = await stp_repo.purchase.get_user_purchases(user_id)
            achievements_sum = await stp_repo.transaction.get_user_achievements_sum(
                user_id
            )
            purchases_sum = await stp_repo.purchase.get_user_purchases_sum(user_id)

            # Рассчитываем уровень
            user_balance = await stp_repo.transaction.get_user_balance(user_id)
            current_level = LevelingSystem.calculate_level(achievements_sum)

            return {
                "level": current_level,
                "balance": user_balance,
                "total_earned": achievements_sum,
                "total_spent": purchases_sum,
                "purchases_count": len(user_purchases),
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики пользователя {user_id}: {e}")
            return {
                "level": 0,
                "balance": 0,
                "total_earned": 0,
                "total_spent": 0,
                "purchases_count": 0,
            }

    @staticmethod
    async def get_group_statistics(head_name: str, stp_repo: MainRequestsRepo) -> dict:
        """Получить общую статистику группы руководителя"""
        try:
            # Получаем сотрудников группы
            group_users = await stp_repo.employee.get_users_by_head(head_name)

            total_points = 0
            group_purchases = {}

            for user in group_users:
                if user.user_id:  # Только авторизованные пользователи
                    # Суммируем очки
                    achievements_sum = (
                        await stp_repo.transaction.get_user_achievements_sum(
                            user.user_id
                        )
                    )
                    total_points += achievements_sum

                    # Собираем статистику предметов
                    most_bought_product = (
                        await stp_repo.purchase.get_most_bought_product(user.user_id)
                    )
                    if most_bought_product:
                        product_name = most_bought_product[0]
                        product_count = most_bought_product[1]
                        group_purchases[product_name] = (
                            group_purchases.get(product_name, 0) + product_count
                        )

            return {
                "total_users": len(group_users),
                "total_points": total_points,
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики группы {head_name}: {e}")
            return {
                "total_users": 0,
                "total_points": 0,
            }

    @staticmethod
    async def get_group_statistics_by_id(
        head_user_id: int, stp_repo: MainRequestsRepo
    ) -> dict:
        """Получить общую статистику группы руководителя по его ID"""
        try:
            # Получаем руководителя по ID
            head_user = await stp_repo.employee.get_user(user_id=head_user_id)
            if not head_user:
                return {
                    "total_users": 0,
                    "total_points": 0,
                    "most_popular_achievement": None,
                    "most_popular_product": None,
                }

            # Используем существующую функцию
            return await SearchService.get_group_statistics(
                head_user.fullname, stp_repo
            )
        except Exception as e:
            logger.error(
                f"Ошибка получения статистики группы по ID {head_user_id}: {e}"
            )
            return {
                "total_users": 0,
                "total_points": 0,
                "most_popular_achievement": None,
                "most_popular_product": None,
            }

    @staticmethod
    def format_user_info_base(
        user: Employee, user_head: Employee = None, stats: dict = None
    ) -> str:
        """
        Формирует базовую информацию о пользователе

        :param user: Сотрудник
        :param user_head: Руководитель (опционально)
        :param stats: Статистика игрока (опционально)
        :return: Отформатированная строка с информацией
        """
        from tgbot.misc.dicts import roles

        # Определение роли
        role_name = roles.get(user.role, "Неизвестная роль")

        # Формирование основной информации о пользователе
        user_info = f"""<b>👤 Информация о сотруднике</b>

<b>ФИО:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>Должность:</b> {user.position} {user.division}"""

        if user_head:
            user_info += f"\n<b>Руководитель:</b> <a href='t.me/{user_head.username}'>{user.head}</a>"

        user_info += f"\n\n🛡️<b>Уровень доступа:</b> {role_name} ({user.role})"

        if user.email:
            user_info += f"\n<b>Рабочая почта:</b> {user.email}"

        # Добавляем статистику уровня (только для специалистов и дежурных)
        if user.user_id and user.role in [1, 3] and stats:
            user_info += f"""

<blockquote expandable><b>📊 Статистика игрока</b>
<b>⚔️ Уровень:</b> {stats["level"]}
<b>✨ Баланс:</b> {stats["balance"]} баллов
<b>📈 Всего заработано:</b> {stats["total_earned"]} баллов
<b>💸 Всего потрачено:</b> {stats["total_spent"]} баллов</blockquote>"""

        return user_info

    @staticmethod
    def format_head_group_info(group_stats: dict) -> str:
        """
        Формирует информацию о группе руководителя

        :param group_stats: Статистика группы
        :return: Дополнительная информация для руководителей
        """
        return f"""

<blockquote expandable><b>👥 Статистика группы</b>
<b>Сотрудников в группе:</b> {group_stats["total_users"]}
<b>Общие очки группы:</b> {group_stats["total_points"]} баллов</blockquote>

<i>💡 Нажми кнопку ниже чтобы увидеть список группы</i>"""
