EMOJI = {
    "hi": "5319016550248751722",
    "calendar": "5274055917766202507",
    "pin": "5397782960512444700",
    "star": "5438496463044752972",
    "lightning": "5456140674028019486",
    "weights": "5400250414929041085",
    "gear": "5341715473882955310",
    "percent": "5229064374403998351",
    "money_bag": "5287231198098117669",
    "abacus": "5190741648237161191",
    "banknote": "5201873447554145566",
    "bank": "5332455502917949981",
    "pig": "5312123810638483121",
    "house": "5416041192905265756",
    "warning": "5447644880824181073",
    "megaphone": "5424818078833715060",
}

EMOJI_FALLBACKS = {
    "hi": "👋",
    "calendar": "📅",
    "pin": "📌",
    "star": "🌟",
    "lightning": "⚡️",
    "weights": "⚖️",
    "gear": "⚙️",
    "percent": "🛍",
    "money_bag": "💰",
    "abacus": "🧮",
    "banknote": "💵",
    "bank": "🏦",
    "pig": "🐷",
    "house": "🏠",
    "warning": "⚠️",
    "megaphone": "📣",
}


def tg_emoji(name: str) -> str:
    """Format emoji for message text (HTML parsing)."""
    return f'<tg-emoji emoji-id="{EMOJI[name]}">{EMOJI_FALLBACKS[name]}</tg-emoji>'
