import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import Employee, Product
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.keyboards.user.game.main import GameMenu
from tgbot.keyboards.user.game.shop import (
    SellProductShopMenu,
    ShopBuy,
    ShopConfirm,
    ShopMenu,
    product_confirmation_kb,
    product_purchase_success_kb,
    shop_kb,
    to_game_kb,
)

user_game_shop_router = Router()
user_game_shop_router.message.filter(
    F.chat.type == "private",
)
user_game_shop_router.callback_query.filter(F.message.chat.type == "private")

logger = logging.getLogger(__name__)


@user_game_shop_router.callback_query(GameMenu.filter(F.menu == "shop"))
async def game_shop_main(
    callback: CallbackQuery,
    user: Employee,
    stp_repo: MainRequestsRepo,
):
    """
    Обработчик клика на меню "Магазин" из игрового профиля
    """
    await game_shop(
        callback=callback,
        user=user,
        callback_data=ShopMenu(menu="available", page=1),
        stp_repo=stp_repo,
    )


@user_game_shop_router.callback_query(ShopMenu.filter(F.menu.in_(["available", "all"])))
async def game_shop(
    callback: CallbackQuery,
    user: Employee,
    callback_data: ShopMenu,
    stp_repo: MainRequestsRepo,
):
    """
    Обработчик клика на меню предметов с фильтрацией
    """

    # Достаём номер страницы и фильтр из callback data
    page = getattr(callback_data, "page", 1)
    filter_type = getattr(callback_data, "menu", "available")

    user_balance = await stp_repo.transaction.get_user_balance(user.user_id)

    # Получаем предметы на основе фильтра
    if filter_type == "available":
        # Получаем только доступные предметы на основе баланса пользователя
        products = await stp_repo.product.get_available_products(user_balance)
        filter_title = "Доступные предметы"
    else:  # filter_type == "all"
        # Получаем все предметы для направления пользователя
        division = "НТП" if "НТП" in user.division else "НЦК"
        products = await stp_repo.product.get_products(division=division)
        filter_title = "Все предметы"

    if not products:
        empty_message = f"""💎 <b>Магазин - {filter_title}</b>

<b>✨ Твой баланс:</b> {user_balance} баллов

{"У тебя недостаточно баллов для покупки предметов 😔" if filter_type == "available" else "В твоем направлении пока нет предметов 😔"}

<i>Заработать баллы можно получая достижения</i>"""

        await callback.message.edit_text(
            empty_message,
            reply_markup=to_game_kb(),
        )
        return

    # Логика пагинации
    products_per_page = 5
    total_products = len(products)
    total_pages = (total_products + products_per_page - 1) // products_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * products_per_page
    end_idx = start_idx + products_per_page
    page_products = products[start_idx:end_idx]

    # Построение списка предметов для текущей страницы
    products_list = []
    for counter, product in enumerate(page_products, start=start_idx + 1):
        # Добавляем иконку доступности если показываем все предметы
        availability_icon = ""
        if filter_type == "all":
            availability_icon = "💰 " if user_balance >= product.cost else "🔒 "

        products_list.append(f"""{counter}. {availability_icon}<b>{product.name}</b>
<blockquote>💵 Стоимость: {product.cost} баллов
📝 Описание: {product.description}""")
        if product.count > 1:
            products_list.append(f"""📍 Активаций: {product.count}""")
        products_list.append("</blockquote>")

    message_text = f"""💎 <b>Магазин - {filter_title}</b>
<i>Страница {page} из {total_pages}</i>

<b>✨ Твой баланс:</b> {user_balance} баллов

{chr(10).join(products_list)}"""

    await callback.message.edit_text(
        message_text,
        reply_markup=shop_kb(
            page, total_pages, page_products, filter_type, user_balance
        ),
    )
    logger.info(
        f"[Пользователь] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыт магазин ({filter_type}), страница {page}, баланс: {user_balance}"
    )


@user_game_shop_router.callback_query(ShopBuy.filter())
async def game_shop_confirmation(
    callback: CallbackQuery,
    callback_data: ShopBuy,
    user: Employee,
    stp_repo: MainRequestsRepo,
):
    """
    Обработчик выбора предмета - показывает окно подтверждения
    """
    product_id = callback_data.product_id
    current_page = callback_data.page

    # Получаем информацию о выбранном предмете
    try:
        product_info = await stp_repo.product.get_product(product_id)
    except Exception as e:
        logger.error(f"Error getting product {product_id}: {e}")
        await callback.answer(
            "❌ Ошибка получения информации о предмете", show_alert=True
        )
        return

    # Получаем баланс пользователя
    user_balance = await stp_repo.transaction.get_user_balance(user.user_id)

    # Проверяем, достаточно ли баллов
    if user_balance < product_info.cost:
        await callback.answer(
            f"❌ Недостаточно баллов!\nУ тебя: {user_balance} баллов\nНужно: {product_info.cost} баллов",
            show_alert=True,
        )
        return

    # Рассчитываем баланс после покупки
    balance_after_purchase = user_balance - product_info.cost

    # Формируем сообщение с подробной информацией
    message_text = f"""<b>🎯 Покупка предмета:</b> {product_info.name}

<b>📝 Описание</b>
{product_info.description}

<b>📍 Количество использований:</b> {product_info.count}

<b>✨ Баланс</b>
• Текущий: {user_balance} баллов
• Спишется: {product_info.cost} баллов
• Останется : {balance_after_purchase} баллов

<i>Купленные предметы можно найти в <b>🎒 Инвентаре</b></i>"""

    await callback.message.edit_text(
        message_text, reply_markup=product_confirmation_kb(product_id, current_page)
    )

    logger.info(
        f"[Подтверждение покупки] {callback.from_user.username} ({user.user_id}) просматривает '{product_info.name}'"
    )


@user_game_shop_router.callback_query(ShopConfirm.filter())
async def game_shop_completed(
    callback: CallbackQuery,
    callback_data: ShopConfirm,
    user: Employee,
    stp_repo: MainRequestsRepo,
):
    """
    Обработчик финального подтверждения покупки предмета
    """
    product_id = callback_data.product_id
    current_page = callback_data.page
    action = callback_data.action

    # Если пользователь выбрал вернуться к списку
    if action == "back":
        # Redirect back to shop page with available filter by default
        await game_shop(
            callback=callback,
            user=user,
            callback_data=ShopMenu(menu="available", page=current_page),
            stp_repo=stp_repo,
        )
        return

    # Если пользователь подтвердил покупку
    if action == "buy":
        # Получаем информацию о предмете
        try:
            product_info: Product = await stp_repo.product.get_product(product_id)
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            await callback.answer(
                "❌ Ошибка получения информации о предмете", show_alert=True
            )
            return

        # Получаем баланс пользователя
        user_balance = await stp_repo.transaction.get_user_balance(user.user_id)

        if user_balance < product_info.cost:
            await callback.answer(
                f"❌ Недостаточно баллов!\nУ тебя: {user_balance}, нужно: {product_info.cost}",
                show_alert=True,
            )
            return

        # Создаем по пользователю с новым статусом "stored"
        try:
            new_purchase = await stp_repo.purchase.add_purchase(
                user_id=user.user_id, product_id=product_id, status="stored"
            )
            await stp_repo.transaction.add_transaction(
                user_id=user.user_id,
                type="spend",
                source_type="product",
                source_id=product_id,
                amount=product_info.cost,
                comment=f"Автоматическая покупка предмета {product_info.name}",
            )

            # Пересчитываем новый баланс
            new_balance = user_balance - product_info.cost

            # Формируем сообщение об успешной покупке с детальной информацией
            success_message = f"""<b>✅ Приобретен предмет:</b> {product_info.name}

<b>📍 Количество активаций:</b> {product_info.count}

<b>✨ Баланс</b>
• Был: {user_balance} баллов  
• Списано: {product_info.cost} баллов
• Стало: {new_balance} баллов

<b>📝 Описание</b>
{product_info.description}

<i>🎯 Ты можешь использовать его сейчас или позже в <b>🎒 Инвентаре</b></i>"""

            # Показываем сообщение с новой клавиатурой
            await callback.message.edit_text(
                success_message,
                reply_markup=product_purchase_success_kb(new_purchase.id),
            )

            logger.info(
                f"[Покупка предмета] {callback.from_user.username} ({user.user_id}) купил предмет '{product_info.name}' за {product_info.cost} баллов со статусом 'stored'"
            )

        except Exception as e:
            logger.error(f"Error creating user purchase: {e}")
            await callback.answer("❌ Ошибка при покупке предмета", show_alert=True)


@user_game_shop_router.callback_query(SellProductShopMenu.filter())
async def sell_product_from_shop(
    callback: CallbackQuery,
    callback_data: SellProductShopMenu,
    user: Employee,
    stp_repo: MainRequestsRepo,
):
    """
    Обработчик продажи предмета из экрана успешной покупки
    """
    user_product_id = callback_data.user_product_id

    # Получаем информацию о предмете
    user_product_detail = await stp_repo.purchase.get_purchase_details(user_product_id)
    if not user_product_detail:
        await callback.answer("❌ Предмет не найден", show_alert=True)
        return

    user_product = user_product_detail.user_purchase
    product_info = user_product_detail.product_info

    # Проверяем, что предмет можно продать (статус "stored" и usage_count = 0)
    if user_product.status != "stored" or user_product.usage_count > 0:
        await callback.answer(
            "❌ Нельзя продать уже использованный предмет", show_alert=True
        )
        return

    try:
        success = await stp_repo.purchase.delete_user_purchase(user_product_id)
        await stp_repo.transaction.add_transaction(
            user_id=user_product.user_id,
            type="earn",
            source_type="product",
            source_id=product_info.id,
            amount=product_info.cost,
            comment=f"Возврат предмета: {product_info.name}",
        )

        if success:
            await callback.answer(
                f"✅ Продано: {product_info.name}.\nВозвращено: {product_info.cost} баллов"
            )

            logger.info(
                f"[Продажа предмета] {user.username} ({user.user_id}) продал предмет '{product_info.name}' за {product_info.cost} баллов"
            )

            # Return to shop since user came from purchase flow
            await game_shop(
                callback=callback,
                user=user,
                callback_data=ShopMenu(menu="available", page=1),
                stp_repo=stp_repo,
            )
        else:
            await callback.answer("❌ Ошибка при продаже предмета", show_alert=True)

    except Exception as e:
        logger.error(f"Error selling product: {e}")
        await callback.answer("❌ Ошибка при продаже предмета", show_alert=True)
