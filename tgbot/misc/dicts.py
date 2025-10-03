roles = {
    0: {"name": "Не авторизован", "emoji": ""},
    1: {"name": "Специалист", "emoji": "👤"},
    2: {"name": "Руководитель", "emoji": "👑"},
    3: {"name": "Дежурный", "emoji": "👮‍♂️"},
    4: {"name": "Администратор", "emoji": "🛡️"},
    5: {"name": "ГОК", "emoji": "🔎"},
    6: {"name": "МИП", "emoji": "📝"},
    10: {"name": "root", "emoji": "⚡"},
}

russian_months = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь",
}

months_emojis = {
    "январь": "❄️",
    "февраль": "💙",
    "март": "🌸",
    "апрель": "🌷",
    "май": "🌻",
    "июнь": "☀️",
    "июль": "🏖️",
    "август": "🌾",
    "сентябрь": "🍂",
    "октябрь": "🎃",
    "ноябрь": "🍁",
    "декабрь": "🎄",
}


def get_prev_month(current_month: str) -> str:
    """Get the previous month name in Russian"""
    try:
        # Create reverse lookup: month name -> month number
        month_to_num = {name: num for num, name in russian_months.items()}

        # Get current month number
        current_num = month_to_num.get(current_month.lower())
        if current_num is None:
            return "сентябрь"

        # Calculate previous month number (1-12, wrapping around)
        prev_num = 12 if current_num == 1 else current_num - 1
        return russian_months[prev_num]
    except (ValueError, KeyError):
        return "сентябрь"
