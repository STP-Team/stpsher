"""Сервис расчета уровней."""

from typing import Tuple


class LevelingSystem:
    """Система уровней, основанная на достижении определенных этапов, с отслеживанием прогресса."""

    # Определяем пул уровней: (минимальный уровень, кол-во баллов за уровень)
    milestones = [
        (0, 100),  # Уровни 1-10: 100 баллов каждый уровень
        (10, 150),  # Уровни 11-20: 150 баллов каждый уровень
        (20, 200),  # Уровни 21-30: 200 баллов каждый уровень
        (30, 300),  # Уровни 31+: 300 баллов каждый уровень
        (40, 400),  # Уровни 41+: 400 баллов каждый уровень
        (50, 500),  # Уровни 51+: 500 баллов каждый уровень
        (60, 600),  # Уровни 61+: 600 баллов каждый уровень
        (70, 700),  # Уровни 71+: 700 баллов каждый уровень
        (80, 800),  # Уровни 81+: 800 баллов каждый уровень
        (90, 900),  # Уровни 91+: 900 баллов каждый уровень
    ]

    @classmethod
    def calculate_level(cls, achievements_sum: int) -> int:
        """Рассчитываем уровень пользователя.

        Args:
            achievements_sum: Общая сумма баллов за достижения

        Returns:
            Текущий уровень пользователя
        """
        if achievements_sum <= 0:
            return 0

        level = 0
        remaining_points = achievements_sum

        for i, (min_level, points_per_level) in enumerate(cls.milestones):
            # Пропускаем если еще не дошли до следующего этапа
            if level < min_level:
                continue

            # Определяем, сколько уровней мы можем получить на текущем этапе пользователя
            if i + 1 < len(cls.milestones):
                # Не последний этап - ограничен следующим этапом
                next_min_level = cls.milestones[i + 1][0]
                max_levels_in_range = next_min_level - level
            else:
                # Последний этап - бесконечные уровни
                max_levels_in_range = float("inf")

            # Рассчитываем уровни, полученные на этом этапе
            levels_gained = min(
                remaining_points // points_per_level, max_levels_in_range
            )
            level += int(levels_gained)
            remaining_points -= int(levels_gained) * points_per_level

            # Если мы не можем пройти еще один уровень на этом этапе - останавливаемся.
            if remaining_points < points_per_level:
                break

        return level

    @classmethod
    def get_level_progress(cls, achievements_sum: int) -> Tuple[int, int, int, int]:
        """Рассчитывает детальный прогресс уровня пользователя.

        Args:
            achievements_sum: Общая сумма баллов за достижения

        Returns:
            Tuple of (current_level, current_level_points, next_level_requirement, points_to_next_level)
            - current_level: Текущий уровень пользователя
            - current_level_points: Очки, заработанные для текущего уровня
            - next_level_requirement: Общее количество очков, необходимое для перехода на следующий уровень
            - points_to_next_level: Очки, необходимые для перехода на следующий уровень
        """
        current_level = cls.calculate_level(achievements_sum)

        if current_level == 0:
            # Обработка если уровень 0
            return 0, achievements_sum, 100, max(0, 100 - achievements_sum)

        # Считаем кол-во баллов для получения текущего уровня
        current_level_total_points = cls._get_total_points_for_level(current_level)

        # Считаем кол-во баллов для получения следующего уровня
        next_level_total_points = cls._get_total_points_for_level(current_level + 1)

        # Баллы, заработанные для перехода на следующий этап (сверх требований текущего уровня)
        current_level_points = achievements_sum - current_level_total_points

        # Баллы, необходимые для перехода на следующий уровень
        next_level_requirement = next_level_total_points - current_level_total_points
        points_to_next_level = max(0, next_level_total_points - achievements_sum)

        return (
            current_level,
            current_level_points,
            next_level_requirement,
            points_to_next_level,
        )

    @classmethod
    def _get_total_points_for_level(cls, target_level: int) -> int:
        """Рассчитывает общее количество баллов, необходимое для достижения определенного уровня.

        Args:
            target_level: Целевой уровень для расчета необходимого кол-ва баллов

        Returns:
            Общее количество очков, необходимое для достижения целевого уровня с уровня 0
        """
        if target_level <= 0:
            return 0

        total_points = 0
        current_level = 0

        for i, (min_level, points_per_level) in enumerate(cls.milestones):
            # Определяем диапазон уровней для этапа
            if i + 1 < len(cls.milestones):
                next_min_level = cls.milestones[i + 1][0]
                max_level_in_range = next_min_level - 1
            else:
                max_level_in_range = float("inf")

            # Если целевой уровень находится в диапазоне этапа
            if target_level <= max_level_in_range:
                # Добавить баллы за уровни от current_level до target_level
                levels_to_add = target_level - max(current_level, min_level)
                total_points += levels_to_add * points_per_level
                break
            else:
                # Добавить все баллы для этого диапазона этапа
                levels_in_range = max_level_in_range + 1 - max(current_level, min_level)
                total_points += levels_in_range * points_per_level
                current_level = max_level_in_range + 1

        return total_points

    @classmethod
    def get_level_info_text(cls, achievements_sum: int, user_balance: int) -> str:
        """Форматирует текст, отображающий прогресс уровня для меню пользователя.

        Args:
            achievements_sum: Общая сумма баллов за достижения
            user_balance: Текущий доступный баланс

        Returns:
            Форматированная строка для отображения информации об уровне пользователя
        """
        current_level, current_points, next_requirement, points_needed = (
            cls.get_level_progress(achievements_sum)
        )

        # Рассчитываем прогресс уровня
        if next_requirement > 0:
            progress_percent = int((current_points / next_requirement) * 100)
            progress_bar = cls._create_progress_bar(progress_percent)
        else:
            progress_percent = 100
            progress_bar = "████████████"

        # Проверяем этап пользователя
        milestone_info = cls._get_milestone_info(current_level)

        level_text = f"""<b>⚔️ Твой уровень:</b> {current_level}
<b>✨ Баланс:</b> {user_balance} баллов

<blockquote><b>📈 Прогресс до {current_level + 1} уровня</b>
{progress_bar} {progress_percent}%
{current_points}/{next_requirement} баллов

<b>💎 До следующего уровня:</b> {points_needed} баллов
{milestone_info}</blockquote>"""

        return level_text

    @classmethod
    def _create_progress_bar(cls, percent: int, length: int = 12) -> str:
        """Создает визуальную строку с прогрессом уровня.

        Args:
            percent: Процент прогресса
            length: Длина строки прогресса

        Returns:
            Строка с прогресс баром
        """
        filled = int((percent / 100) * length)
        empty = length - filled
        return "█" * filled + "░" * empty

    @classmethod
    def _get_milestone_info(cls, current_level: int) -> str:
        """Получает информацию о том, к какому этапу относится текущий уровень.

        Args:
            current_level: Текущий уровень пользователя

        Returns:
            Отформатированная строка с информацией о текущем прогрессе
        """
        # Определяем, к какому этапу относится уровень
        for i, (min_level, points_per_level) in enumerate(cls.milestones):
            if i + 1 < len(cls.milestones):
                next_min_level = cls.milestones[i + 1][0]
                # Проверяем, находится ли текущий уровень в диапазоне этапа
                if min_level <= current_level < next_min_level:
                    return f"<i>Этап: {min_level + 1}-{next_min_level} уровни ({points_per_level} очков/уровень)</i>"
            else:
                # Последний этап — если текущий уровень >= min_level
                if current_level >= min_level:
                    return f"<i>Этап: {min_level + 1}+ уровни ({points_per_level} очков/уровень)</i>"

        # Фоллбек - если не удастся рассчитать текущий этап
        return f"<i>Этап: 1-10 уровни ({cls.milestones[0][1]} очков/уровень)</i>"
