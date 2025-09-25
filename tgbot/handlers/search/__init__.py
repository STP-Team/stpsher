from aiogram import Router

from .main import search_router


def register_search_handlers() -> Router:
    """Регистрация всех роутеров поиска"""
    router = Router()

    # Основной роутер поиска
    router.include_router(search_router)

    return router
