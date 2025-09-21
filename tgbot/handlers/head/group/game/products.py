import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import HeadFilter
from tgbot.handlers.gok.game.main import filter_items_by_division
from tgbot.keyboards.head.group.game.main import HeadGameMenu
from tgbot.keyboards.head.group.game.products import head_products_paginated_kb
from tgbot.keyboards.mip.game.main import (
    FilterToggleMenu,
    ProductsMenu,
    PurchaseActionMenu,
    PurchaseActivationMenu,
    parse_filters,
    toggle_filter,
)
from tgbot.keyboards.mip.game.purchases import (
    purchase_activation_kb,
    purchase_detail_kb,
)
from tgbot.keyboards.user.main import MainMenu

head_game_products_router = Router()
head_game_products_router.message.filter(F.chat.type == "private", HeadFilter())
head_game_products_router.callback_query.filter(
    F.message.chat.type == "private", HeadFilter()
)

logger = logging.getLogger(__name__)


@head_game_products_router.callback_query(HeadGameMenu.filter(F.menu == "products"))
async def head_products_menu(callback: CallbackQuery, stp_repo: MainRequestsRepo):
    """
    Обработчик клика на меню предметов - перенаправляет на products_all с дефолтными параметрами
    """
    # Создаем callback_data с дефолтными параметрами
    from tgbot.keyboards.mip.game.main import ProductsMenu

    new_callback_data = ProductsMenu(menu="products_all", page=1, filters="НЦК,НТП")

    # Вызываем основной обработчик
    await head_products_all(callback, new_callback_data, stp_repo)


@head_game_products_router.callback_query(ProductsMenu.filter(F.menu == "products_all"))
async def head_products_all(
    callback: CallbackQuery, callback_data: ProductsMenu, stp_repo: MainRequestsRepo
):
    """
    Обработчик клика на меню всех возможных предметов для руководителей
    Руководители видят все предметы из всех направлений с возможностью фильтрации
    """

    # Достаём параметры из callback data
    page = getattr(callback_data, "page", 1)
    filters = getattr(callback_data, "filters", "НЦК,НТП")

    # Парсим активные фильтры
    active_filters = parse_filters(filters)

    # Получаем ВСЕ предметы без фильтрации по направлению
    all_products = await stp_repo.product.get_products()

    # Применяем фильтрацию
    filtered_products = filter_items_by_division(all_products, active_filters)

    # Логика пагинации
    products_per_page = 5
    total_products = len(filtered_products)
    total_pages = (total_products + products_per_page - 1) // products_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * products_per_page
    end_idx = start_idx + products_per_page
    page_products = filtered_products[start_idx:end_idx]

    # Построение списка предметов для текущей страницы
    products_list = []
    for counter, product in enumerate(page_products, start=start_idx + 1):
        product_text = f"""
<b>{counter}. {product.name}</b>
<blockquote>📍 Активаций: {product.count}
💵 Стоимость: {product.cost} баллов
🔰 Направление: {product.division}
📝 Описание: {product.description}</blockquote>"""
        products_list.append(product_text)

    # Статистика
    stats_ntp = sum(1 for product in all_products if product.division == "НТП")
    stats_nck = sum(1 for product in all_products if product.division == "НЦК")
    filtered_stats = f"Показано: {total_products}"

    message_text = f"""
<b>👏 Все возможные предметы</b>
<i>Страница {page} из {total_pages}</i>

<blockquote expandable><b>Всего предметов:</b>  
• НТП: {stats_ntp}  
• НЦК: {stats_nck}  
{filtered_stats}
</blockquote>{chr(10).join(products_list)}
    """

    await callback.message.edit_text(
        message_text,
        reply_markup=head_products_paginated_kb(page, total_pages, filters),
    )
    logger.info(
        f"[Руководитель] - [Предметы] {callback.from_user.username} ({callback.from_user.id}): Просмотр предметов, страница {page}, фильтры: {filters}"
    )


@head_game_products_router.callback_query(
    FilterToggleMenu.filter(F.menu == "products_all")
)
async def head_products_toggle_filter(
    callback: CallbackQuery, callback_data: FilterToggleMenu, stp_repo: MainRequestsRepo
):
    """Обработчик переключения фильтров для предметов"""
    menu = callback_data.menu
    filter_name = callback_data.filter_name
    current_filters = callback_data.current_filters

    # Переключаем фильтр
    new_filters = toggle_filter(current_filters, filter_name)

    # Переходим на первую страницу при изменении фильтров
    if menu == "products_all":
        await head_products_all(
            callback,
            ProductsMenu(menu="products_all", page=1, filters=new_filters),
            stp_repo,
        )


@head_game_products_router.callback_query(
    MainMenu.filter(F.menu == "products_activation")
)
async def head_purchase_activation(
    callback: CallbackQuery,
    callback_data: MainMenu,
    user: Employee,
    stp_repo: MainRequestsRepo,
):
    """
    Обработчик меню покупок для активации руководителями
    Показывает покупки со статусом "review" и manager_role == 7 (Руководители)
    Фильтрует по направлению пользователя
    """

    # Достаём номер страницы из callback data, стандартно = 1
    page = getattr(callback_data, "page", 1)

    # Определяем направление пользователя для фильтрации
    user_division = "НЦК" if "НЦК" in user.division else "НТП"

    # Получаем покупки, ожидающие активации с manager_role == 3
    review_purchases = await stp_repo.purchase.get_review_purchases_for_activation(
        manager_role=3
    )

    # Фильтруем покупки по направлению руководителя
    # Руководитель может видеть только покупки предметов из своего направления
    division_filtered_purchases = []
    for purchase_details in review_purchases:
        product = purchase_details.product_info
        if product.division == user_division:
            division_filtered_purchases.append(purchase_details)

    review_purchases = division_filtered_purchases

    if not review_purchases:
        await callback.message.edit_text(
            """<b>✍️ Активация предметов</b>

Нет предметов, ожидающих активации 😊""",
            reply_markup=purchase_activation_kb(page, 0, []),
        )
        return

    # Логика пагинации
    purchases_per_page = 5
    total_purchases = len(review_purchases)
    total_pages = (total_purchases + purchases_per_page - 1) // purchases_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * purchases_per_page
    end_idx = start_idx + purchases_per_page
    page_purchases = review_purchases[start_idx:end_idx]

    # Построение списка покупок для текущей страницы
    purchases_list = []
    for counter, purchase_details in enumerate(page_purchases, start=start_idx + 1):
        purchase = purchase_details.user_purchase
        product = purchase_details.product_info

        # Получаем информацию о пользователе
        employee = await stp_repo.employee.get_user(user_id=purchase.user_id)
        user_name = employee.fullname if employee else f"ID: {purchase.user_id}"

        if employee.username:
            purchases_list.append(f"""{counter}. <b>{product.name}</b> - {purchase.bought_at.strftime("%d.%m.%Y в %H:%M")}
<blockquote><b>👤 Специалист</b>
<a href='t.me/{employee.username}'>{user_name}</a> из {product.division}

<b>📝 Описание</b>
{product.description}</blockquote>""")
        else:
            purchases_list.append(f"""{counter}. <b>{product.name}</b> - {purchase.bought_at.strftime("%d.%m.%Y в %H:%M")}
<blockquote><b>👤 Специалист</b>
<a href='tg://user?id={employee.user_id}'>{user_name}</a> из {product.division}

<b>📝 Описание</b>
{product.description}</blockquote>""")
        purchases_list.append("")

    message_text = f"""<b>✍️ Активация предметов</b>
<i>Страница {page} из {total_pages}</i>

{chr(10).join(purchases_list)}"""

    await callback.message.edit_text(
        message_text,
        reply_markup=purchase_activation_kb(page, total_pages, page_purchases),
    )

    logger.info(
        f"[Руководитель] - [Активация] {callback.from_user.username} ({callback.from_user.id}): Просмотр активации предметов, страница {page}, направление: {user_division}"
    )


@head_game_products_router.callback_query(PurchaseActivationMenu.filter())
async def head_purchase_activation_detail(
    callback: CallbackQuery,
    callback_data: PurchaseActivationMenu,
    stp_repo: MainRequestsRepo,
):
    """Показывает детальную информацию о покупке для активации руководителем"""
    purchase_id = callback_data.purchase_id
    current_page = callback_data.page

    # Получаем информацию о конкретной покупке
    purchase_details = await stp_repo.purchase.get_purchase_details(purchase_id)

    if not purchase_details:
        await callback.message.edit_text(
            """<b>✍️ Активация предмета</b>

Не смог найти описание для предмета ☹""",
            reply_markup=purchase_detail_kb(purchase_id, current_page),
        )
        return

    purchase = purchase_details.user_purchase
    product = purchase_details.product_info

    # Получаем информацию о пользователе
    employee: Employee = await stp_repo.employee.get_user(user_id=purchase.user_id)
    user_head: Employee = await stp_repo.employee.get_user(fullname=employee.head)

    user_info = (
        f"<a href='t.me/{employee.username}'>{employee.fullname}</a>"
        if employee and employee.username
        else "-"
    )
    head_info = (
        f"<a href='t.me/{user_head.username}'>{employee.head}</a>"
        if user_head and user_head.username
        else "-"
    )

    message_text = f"""
<b>🎯 Активация предмета</b>

<b>🏆 О предмете</b>
<blockquote><b>Название</b>
{product.name}

<b>📝 Описание</b>
{product.description}

<b>💵 Стоимость</b>
{product.cost} баллов

<b>📍 Активаций</b>
{purchase.usage_count} ➡️ {purchase.usage_count + 1} ({product.count} всего)</blockquote>"""

    message_text += f"""

<b>👤 О специалисте</b>
<blockquote><b>ФИО</b>
{user_info}

<b>Должность</b>
{employee.position} {employee.division}

<b>Руководитель</b>
{head_info}</blockquote>

<b>📅 Дата покупки</b>
{purchase.bought_at.strftime("%d.%m.%Y в %H:%M")}
"""
    await callback.message.edit_text(
        message_text,
        reply_markup=purchase_detail_kb(purchase_id, current_page, context="head"),
    )


@head_game_products_router.callback_query(PurchaseActionMenu.filter())
async def head_purchase_action(
    callback: CallbackQuery,
    callback_data: PurchaseActionMenu,
    stp_repo: MainRequestsRepo,
    user: Employee,
):
    """Обработка подтверждения/отклонения покупки руководителем"""
    purchase_id = callback_data.purchase_id
    action = callback_data.action
    current_page = callback_data.page

    try:
        # Получаем информацию о покупке
        purchase_details = await stp_repo.purchase.get_purchase_details(purchase_id)

        if not purchase_details:
            await callback.answer("❌ Покупка не найдена", show_alert=True)
            return

        purchase = purchase_details.user_purchase
        product = purchase_details.product_info
        employee_user: Employee = await stp_repo.employee.get_user(
            user_id=purchase.user_id
        )

        if action == "approve":
            # Подтверждаем покупку
            await stp_repo.purchase.approve_purchase_usage(
                purchase_id=purchase_id,
                updated_by_user_id=callback.from_user.id,
            )

            await callback.answer(
                f"""✅ Предмет '{product.name}' активирован!

Специалист {employee_user.fullname} был уведомлен об изменении статуса""",
                show_alert=True,
            )

            if purchase.usage_count >= product.count:
                employee_notify_message = f"""<b>👌 Предмет активирован:</b> {product.name}

Руководитель <a href='t.me/{user.username}'>{user.fullname}</a> подтвердил активацию предмета

У <b>{product.name}</b> не осталось использований

<i>Купить его повторно можно в <b>💎 Магазине</b></i>"""
            else:
                employee_notify_message = f"""<b>👌 Предмет активирован:</b> {product.name}

Руководитель <a href='t.me/{user.username}'>{user.fullname}</a> подтвердил активацию предмета

📍 Осталось активаций: {product.count - purchase.usage_count} из {product.count}"""

            await callback.bot.send_message(
                chat_id=employee_user.user_id,
                text=employee_notify_message,
            )

            logger.info(
                f"[Руководитель] - [Подтверждение] {callback.from_user.username} ({callback.from_user.id}) подтвердил {product.name} для пользователя {employee_user.username} ({purchase.user_id})"
            )

        elif action == "reject":
            # Отклоняем покупку
            await stp_repo.purchase.reject_purchase_usage(
                purchase_id=purchase_id, updated_by_user_id=callback.from_user.id
            )

            await callback.answer(
                f"""❌ Активация предмета '{product.name}' отклонена

Специалист {employee_user.fullname} был уведомлен об изменении статуса""",
                show_alert=True,
            )

            await callback.bot.send_message(
                chat_id=employee_user.user_id,
                text=f"""<b>Активация отменена:</b> {product.name}

Руководитель <a href='t.me/{user.username}'>{user.fullname}</a> отменил активацию <b>{product.name}</b>

<i>Использование предмета не будет засчитано</i>""",
            )

            logger.info(
                f"[Руководитель] - [Отклонение] {callback.from_user.username} ({callback.from_user.id}) отклонил активацию {product.name} для пользователя {employee_user.username} ({purchase.user_id})"
            )

        # Возвращаемся к списку покупок для активации
        await head_purchase_activation(
            callback=callback,
            callback_data=MainMenu(menu="products_activation", page=current_page),
            user=user,
            stp_repo=stp_repo,
        )

    except Exception as e:
        logger.error(f"Error updating purchase status: {e}")
        await callback.answer("❌ Ошибка при обработке покупки", show_alert=True)
