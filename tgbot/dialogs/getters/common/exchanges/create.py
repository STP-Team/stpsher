from typing import Any

from aiogram_dialog import DialogManager


async def exchange_types_getter(
    dialog_manager: DialogManager, **_kwargs
) -> dict[str, Any]:
    """Геттер для типов предложения.

    Returns:
        Словарь со списком доступных типов предложения
    """
    return {
        "exchange_types": [
            ("buy", "📈 Купить"),
            ("sell", "📉 Продать"),
        ]
    }
