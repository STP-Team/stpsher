import random
import string


def generate_auth_code(length=6):
    chars = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return "".join(random.choice(chars) for _ in range(length))


def calculate_level(achievements_sum: int) -> int:
    """
    Расчет уровня пользователя исходя из его суммы баллов и системы milestones
    :param achievements_sum: Сумма баллов пользователя
    :return: Уровень пользователя
    """
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
        (90, 900),  # Уровни 91+: 9000 баллов каждый уровень
    ]

    level = 0
    remaining_points = achievements_sum

    for min_level, points_per_level in milestones:
        if level < min_level:
            continue

        levels_in_range = min(
            remaining_points // points_per_level,
            float("inf")
            if min_level == milestones[-1][0]
            else milestones[milestones.index((min_level, points_per_level)) + 1][0]
            - min_level,
        )

        level += int(levels_in_range)
        remaining_points -= int(levels_in_range) * points_per_level

        if remaining_points < points_per_level:
            break

    return level
