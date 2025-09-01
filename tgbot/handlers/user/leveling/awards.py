import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.keyboards.mip.leveling.awards import award_notify_kb
from tgbot.keyboards.mip.leveling.main import LevelingMenu
from tgbot.keyboards.user.leveling.awards import (
    AwardDetailMenu,
    AwardHistoryMenu,
    AwardPurchaseConfirmMenu,
    AwardPurchaseMenu,
    AwardsMenu,
    CancelActivationMenu,
    DutyActivationListMenu,
    DutyAwardActionMenu,
    DutyAwardActivationMenu,
    SellAwardMenu,
    UseAwardMenu,
    available_awards_paginated_kb,
    award_confirmation_kb,
    award_detail_back_kb,
    award_detail_kb,
    award_history_kb,
    award_purchase_success_kb,
    awards_kb,
    awards_paginated_kb,
    duty_award_activation_kb,
    duty_award_detail_kb,
    to_awards_kb,
)
from tgbot.keyboards.user.main import MainMenu
from tgbot.misc.dicts import executed_codes
from tgbot.services.broadcaster import broadcast


def get_status_emoji(status: str) -> str:
    """Возвращает эмодзи в зависимости от статуса"""
    status_emojis = {
        "stored": "📦",
        "review": "⏳",
        "used_up": "🔒",
        "canceled": "🔥",
        "rejected": "⛔",
    }
    return status_emojis.get(status, "❓")


user_leveling_awards_router = Router()
user_leveling_awards_router.message.filter(
    F.chat.type == "private",
)
user_leveling_awards_router.callback_query.filter(F.message.chat.type == "private")

logger = logging.getLogger(__name__)


@user_leveling_awards_router.callback_query(MainMenu.filter(F.menu == "awards"))
async def user_awards_cb(callback: CallbackQuery, user: User):
    await callback.message.edit_text(
        """<b>👏 Награды</b>

Здесь ты можешь найти доступные для приобретения, а так же все возможные награды

<i>Для покупки наград нужны баллы
Баллы можно получать за <b>🎯 Достижения</b></i>""",
        reply_markup=awards_kb(user),
    )


@user_leveling_awards_router.callback_query(AwardsMenu.filter(F.menu == "all"))
async def awards_all(
    callback: CallbackQuery,
    user: User,
    callback_data: AwardsMenu,
    stp_repo: MainRequestsRepo,
):
    """
    Обработчик клика на меню всех возможных наград
    """

    # Достаём номер страницы из callback data, стандартно = 1
    page = getattr(callback_data, "page", 1)

    all_awards = await stp_repo.award.get_awards(
        division="НТП" if "НТП" in user.division else "НЦК"
    )

    # Логика пагинации
    awards_per_page = 5
    total_awards = len(all_awards)
    total_pages = (total_awards + awards_per_page - 1) // awards_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * awards_per_page
    end_idx = start_idx + awards_per_page
    page_awards = all_awards[start_idx:end_idx]

    # Построение списка наград для текущей страницы
    awards_list = []
    for counter, award in enumerate(page_awards, start=start_idx + 1):
        awards_list.append(f"""{counter}. <b>{award.name}</b>
💵 Стоимость: {award.cost}
📝 Описание: {award.description}""")
        if award.count > 1:
            awards_list.append(f"""📍 Активаций: {award.count}""")
        awards_list.append("")

    message_text = f"""<b>🏆 Все возможные награды</b>
<i>Страница {page} из {total_pages}</i>

{"\n".join(awards_list)}"""

    await callback.message.edit_text(
        message_text, reply_markup=awards_paginated_kb(page, total_pages)
    )
    logger.info(
        f"[Пользователь] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыто меню всех наград, страница {page}"
    )


@user_leveling_awards_router.callback_query(AwardsMenu.filter(F.menu == "available"))
async def awards_available(
    callback: CallbackQuery,
    user: User,
    callback_data: AwardsMenu,
    stp_repo: MainRequestsRepo,
):
    """
    Обработчик клика на меню доступных для покупки наград
    """

    # Достаём номер страницы из callback data, стандартно = 1
    page = getattr(callback_data, "page", 1)

    user_balance = await stp_repo.transactions.get_user_balance(user.user_id)

    # Получаем доступные награды на основе баланса пользователя
    available_awards = await stp_repo.award.get_available_awards(user_balance)

    if not available_awards:
        await callback.message.edit_text(
            f"""<b>❇️ Доступные награды</b>

<b>💰 Твой баланс:</b> {user_balance} баллов

У тебя недостаточно баллов для покупки доступных наград 😔

<i>Заработать баллы можно получая достижения</i>""",
            reply_markup=to_awards_kb(),
        )
        return

    # Логика пагинации
    awards_per_page = 5
    total_awards = len(available_awards)
    total_pages = (total_awards + awards_per_page - 1) // awards_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * awards_per_page
    end_idx = start_idx + awards_per_page
    page_awards = available_awards[start_idx:end_idx]

    # Построение списка наград для текущей страницы
    awards_list = []
    for counter, award in enumerate(page_awards, start=start_idx + 1):
        awards_list.append(f"""{counter}. <b>{award.name}</b>
💵 Стоимость: {award.cost} баллов
📝 Описание: {award.description}""")
        if award.count > 1:
            awards_list.append(f"""📍 Активаций: {award.count}""")
        awards_list.append("")

    message_text = f"""<b>❇️ Доступные награды</b>
<i>Страница {page} из {total_pages}</i>

<b>💰 Твой баланс:</b> {user_balance} баллов

{"\n".join(awards_list)}"""

    await callback.message.edit_text(
        message_text,
        reply_markup=available_awards_paginated_kb(page, total_pages, page_awards),
    )
    logger.info(
        f"[Пользователь] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыто меню доступных наград, страница {page}, баланс: {user_balance}"
    )


@user_leveling_awards_router.callback_query(AwardsMenu.filter(F.menu == "executed"))
async def awards_history(callback: CallbackQuery, stp_repo: MainRequestsRepo):
    """Показывает историю наград пользователя в виде клавиатуры с пагинацией"""
    user_awards_with_details = await stp_repo.user_award.get_user_awards_with_details(
        user_id=callback.from_user.id
    )

    if not user_awards_with_details:
        await callback.message.edit_text(
            """<b>✴️ Купленные награды</b>

Здесь ты найдешь все приобретенные награды, а так же их статус и многое другое

У тебя пока нет купленных наград 🙂

<i>Купить награды можно найти в меню <b>❇️ Доступные</b></i>""",
            reply_markup=to_awards_kb(),
        )
        return

    # Показываем первую страницу по умолчанию
    total_awards = len(user_awards_with_details)
    message_text = f"""<b>✴️ Купленные награды</b>

Здесь ты найдешь все приобретенные награды, а так же их статус и многое другое

<i>Всего наград приобретено: {total_awards}</i>"""

    await callback.message.edit_text(
        message_text,
        reply_markup=award_history_kb(user_awards_with_details, current_page=1),
    )


@user_leveling_awards_router.callback_query(AwardHistoryMenu.filter())
async def awards_history_pagination(
    callback: CallbackQuery, callback_data: AwardHistoryMenu, stp_repo: MainRequestsRepo
):
    """Обработчик пагинации истории наград"""
    page = callback_data.page

    user_awards_with_details = await stp_repo.user_award.get_user_awards_with_details(
        user_id=callback.from_user.id
    )

    if not user_awards_with_details:
        await callback.message.edit_text(
            """<b>✴️ Купленные награды</b>

У тебя пока нет купленных наград 🙂""",
            reply_markup=award_detail_back_kb(),
        )
        return

    total_awards = len(user_awards_with_details)
    message_text = f"""<b>✴️ Купленные награды</b>

Здесь ты найдешь все приобретенные награды, а так же их статус и многое другое

<i>Всего наград приобретено: {total_awards}</i>"""

    await callback.message.edit_text(
        message_text,
        reply_markup=award_history_kb(user_awards_with_details, current_page=page),
    )


@user_leveling_awards_router.callback_query(AwardDetailMenu.filter())
async def award_detail_view(
    callback: CallbackQuery, callback_data: AwardDetailMenu, stp_repo: MainRequestsRepo
):
    """Обработчик детального просмотра награды пользователя"""
    user_award_id = callback_data.user_award_id

    # Получаем информацию о награде
    user_award_detail = await stp_repo.user_award.get_user_award_detail(user_award_id)

    if not user_award_detail:
        await callback.message.edit_text(
            """<b>🏆 Награды</b>

Не смог найти описание для награды ☹""",
            reply_markup=award_detail_back_kb(),
        )
        return

    user_award = user_award_detail.user_award
    award_info = user_award_detail.award_info

    status_names = {
        "stored": "Готова к использованию",
        "review": "На проверке",
        "used_up": "Полностью использована",
        "canceled": "Отменена",
        "rejected": "Отклонена",
    }
    status_name = status_names.get(user_award.status, "Неизвестный статус")

    # Проверяем различные возможности с наградой
    can_use = (
        user_award.status == "stored"
        and user_award_detail.current_usages < user_award_detail.max_usages
    )

    # Можно продать только если статус "stored" И usage_count равен 0 (не использовалась)
    can_sell = user_award.status == "stored" and user_award.usage_count == 0

    # Можно отменить активацию если статус "review" (на проверке)
    can_cancel = user_award.status == "review"

    # Формируем сообщение с подробной информацией
    message_text = f"""
<b>🏆 Награда:</b> {award_info.name}

<b>📊 Статус</b>  
{status_name}

<b>📍 Активаций</b>
{user_award.usage_count} из {award_info.count}

<b>💵 Стоимость</b>  
{award_info.cost} баллов

<b>📝 Описание</b>  
{award_info.description}

<blockquote expandable><b>📅 Дата покупки</b>  
{user_award.bought_at.strftime("%d.%m.%Y в %H:%M")}</blockquote>"""

    if user_award.comment:
        message_text += f"\n\n<b>💬 Комментарий</b>\n└ {user_award.comment}"

    if user_award.updated_by_user_id:
        manager = await stp_repo.user.get_user(user_id=user_award.updated_by_user_id)
        if manager.username:
            message_text += (
                f"\n\n<blockquote expandable><b>👤 Последний проверяющий</b>\n<a href='t.me/{manager.username}'>"
                f"{manager.fullname}</a>"
            )
        else:
            message_text += (
                f"\n\n<blockquote expandable><b>👤 Последний проверяющий</b>\n<a href='tg://user?id={manager.user_id}'>"
                f"{manager.fullname}</a>"
            )
        message_text += f"\n\n<b>📅 Дата проверки</b>\n{user_award.updated_at.strftime('%d.%m.%Y в %H:%M')}</blockquote>"

    # Updated keyboard logic
    keyboard = award_detail_kb(
        user_award.id,
        can_use=can_use,
        can_sell=can_sell,
        can_cancel=can_cancel,
        source_menu="bought",
    )

    await callback.message.edit_text(message_text, reply_markup=keyboard)


@user_leveling_awards_router.callback_query(AwardPurchaseMenu.filter())
async def award_confirmation_handler(
    callback: CallbackQuery,
    callback_data: AwardPurchaseMenu,
    user: User,
    stp_repo: MainRequestsRepo,
):
    """
    Обработчик выбора награды - показывает окно подтверждения
    """
    award_id = callback_data.award_id
    current_page = callback_data.page

    # Получаем информацию о выбранной награде
    try:
        award_info = await stp_repo.award.get_award(award_id)
    except Exception as e:
        logger.error(f"Error getting award {award_id}: {e}")
        await callback.answer(
            "❌ Ошибка получения информации о награде", show_alert=True
        )
        return

    # Получаем баланс пользователя
    user_balance = await stp_repo.transactions.get_user_balance(user.user_id)

    # Проверяем, достаточно ли баллов
    if user_balance < award_info.cost:
        await callback.answer(
            f"❌ Недостаточно баллов!\nУ вас: {user_balance} баллов\nНужно: {award_info.cost} баллов",
            show_alert=True,
        )
        return

    # Рассчитываем баланс после покупки
    balance_after_purchase = user_balance - award_info.cost

    # Формируем сообщение с подробной информацией
    message_text = f"""<b>🎯 Покупка награды:</b> {award_info.name}

<b>📝 Описание</b>
{award_info.description}

<b>📍 Количество использований:</b> {award_info.count}

<b>💰 Баланс</b>
• Текущий: {user_balance} баллов
• Спишется: {award_info.cost} баллов
• Останется : {balance_after_purchase} баллов

<i>Купленные награды можно найти в меню <b>✴️ Купленные</b></i>"""

    await callback.message.edit_text(
        message_text, reply_markup=award_confirmation_kb(award_id, current_page)
    )

    logger.info(
        f"[Подтверждение награды] {callback.from_user.username} ({user.user_id}) просматривает награду '{award_info.name}'"
    )


@user_leveling_awards_router.callback_query(AwardPurchaseConfirmMenu.filter())
async def award_purchase_final_handler(
    callback: CallbackQuery,
    callback_data: AwardPurchaseConfirmMenu,
    user: User,
    stp_repo: MainRequestsRepo,
):
    """
    Обработчик финального подтверждения покупки награды
    """
    award_id = callback_data.award_id
    current_page = callback_data.page
    action = callback_data.action

    # Если пользователь выбрал вернуться к списку
    if action == "back":
        await awards_available(
            callback=callback,
            user=user,
            callback_data=AwardsMenu(menu="available", page=current_page),
            stp_repo=stp_repo,
        )
        return

    # Если пользователь подтвердил покупку
    if action == "buy":
        # Получаем информацию о награде
        try:
            award_info = await stp_repo.award.get_award(award_id)
        except Exception as e:
            logger.error(f"Error getting award {award_id}: {e}")
            await callback.answer(
                "❌ Ошибка получения информации о награде", show_alert=True
            )
            return

        # Получаем баланс пользователя
        user_balance = await stp_repo.transactions.get_user_balance(user.user_id)

        if user_balance < award_info.cost:
            await callback.answer(
                f"❌ Недостаточно баллов!\nУ тебя: {user_balance}, нужно: {award_info.cost}",
                show_alert=True,
            )
            return

        # Создаем награду пользователю с новым статусом "stored"
        try:
            new_user_award = await stp_repo.user_award.create_user_award(
                user_id=user.user_id, award_id=award_id, status="stored"
            )

            # Пересчитываем новый баланс
            new_balance = user_balance - award_info.cost

            # Формируем сообщение об успешной покупке с детальной информацией
            success_message = f"""<b>✅ Приобретена награда:</b> {award_info.name}

<b>📍 Количество активаций:</b> {award_info.count}

<b>💰 Баланс</b>
• Был: {user_balance} баллов  
• Списано: {award_info.cost} баллов
• Стало: {new_balance} баллов

<b>📝 Описание</b>
{award_info.description}

<i>🎯 Ты можешь использовать награду сейчас или найти её позже в меню <b>✴️ Купленные</b></i>"""

            # Показываем сообщение с новой клавиатурой
            await callback.message.edit_text(
                success_message,
                reply_markup=award_purchase_success_kb(new_user_award.id),
            )

            logger.info(
                f"[Покупка награды] {callback.from_user.username} ({user.user_id}) купил награду '{award_info.name}' за {award_info.cost} баллов со статусом 'stored'"
            )

        except Exception as e:
            logger.error(f"Error creating user award: {e}")
            await callback.answer("❌ Ошибка при покупке награды", show_alert=True)


@user_leveling_awards_router.callback_query(UseAwardMenu.filter())
async def use_award_handler(
    callback: CallbackQuery,
    callback_data: UseAwardMenu,
    user: User,
    stp_repo: MainRequestsRepo,
):
    """
    Хендлер нажатия на "Использовать награду" в открытой информации о приобретенной награде
    :param callback:
    :param callback_data:
    :param user:
    :param stp_repo:
    :return:
    """
    user_award_id = callback_data.user_award_id

    # Получаем информацию о награде
    user_award_detail = await stp_repo.user_award.get_user_award_detail(user_award_id)
    if not user_award_detail:
        await callback.answer("❌ Награда не найдена", show_alert=True)
        return

    success = await stp_repo.user_award.use_award(user_award_id)

    if success:
        award_name = user_award_detail.award_info.name
        role_lookup = {v: k for k, v in executed_codes.items()}
        confirmer = role_lookup.get(
            user_award_detail.award_info.manager_role, "Неизвестно"
        )

        await callback.answer(
            f"✅ Награда {award_name} отправлена на рассмотрение!\n\n"
            f"🔔 На проверке у: {confirmer}",
            show_alert=True,
        )

        if user_award_detail.award_info.manager_role == 3:
            award_managers = await stp_repo.user.get_users_by_role(
                role=user_award_detail.award_info.manager_role,
                division=user_award_detail.award_info.division,
            )
        else:
            award_managers = await stp_repo.user.get_users_by_role(
                role=user_award_detail.award_info.manager_role
            )

        manager_ids = [
            manager.user_id
            for manager in award_managers
            if manager.user_id
            and manager.user_id != user_award_detail.user_award.user_id
        ]

        if manager_ids:
            notification_text = f"""<b>🔔 Новая заявка на награду</b>

<b>🏆 Награда:</b> {award_name}
<b>👤 Заявитель:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>📋 Описание:</b> {user_award_detail.award_info.description}

<b>Требуется рассмотрение заявки</b>"""

            result = await broadcast(
                bot=callback.bot,
                users=manager_ids,
                text=notification_text,
                reply_markup=award_notify_kb(),
            )

            logger.info(
                f"[Использование награды] {user.username} ({user.user_id}) отправил на рассмотрение награду '{award_name}'. Уведомлено менеджеров: {result} из {len([m for m in award_managers if m.user_id])}"
            )
    else:
        await callback.answer("❌ Невозможно использовать награду", show_alert=True)

    # Refresh the award detail view
    await award_detail_view(
        callback, AwardDetailMenu(user_award_id=user_award_id), stp_repo
    )


@user_leveling_awards_router.callback_query(SellAwardMenu.filter())
async def sell_award_handler(
    callback: CallbackQuery,
    callback_data: SellAwardMenu,
    user: User,
    stp_repo: MainRequestsRepo,
):
    """
    Хендлер продажи награды - удаляет запись из БД и возвращает баллы
    """
    user_award_id = callback_data.user_award_id
    source_menu = callback_data.source_menu

    # Получаем информацию о награде
    user_award_detail = await stp_repo.user_award.get_user_award_detail(user_award_id)
    if not user_award_detail:
        await callback.answer("❌ Награда не найдена", show_alert=True)
        return

    user_award = user_award_detail.user_award
    award_info = user_award_detail.award_info

    # Проверяем, что награду можно продать (статус "stored" и usage_count = 0)
    if user_award.status != "stored" or user_award.usage_count > 0:
        await callback.answer(
            "❌ Нельзя продать уже использованную награду", show_alert=True
        )
        return

    try:
        success = await stp_repo.user_award.delete_user_award(user_award_id)

        if success:
            await callback.answer(
                f"✅ Продано: {award_info.name}.\nВозвращено: {award_info.cost} баллов"
            )

            logger.info(
                f"[Продажа награды] {user.username} ({user.user_id}) продал награду '{award_info.name}' за {award_info.cost} баллов"
            )

            # Context-aware navigation
            if source_menu == "available":
                # Return to available awards if user came from purchase flow
                await awards_available(
                    callback=callback,
                    user=user,
                    callback_data=AwardsMenu(menu="available", page=1),
                    stp_repo=stp_repo,
                )
            else:
                # Return to bought awards if user came from bought awards menu
                await awards_history(
                    callback=callback,
                    stp_repo=stp_repo,
                )
        else:
            await callback.answer("❌ Ошибка при продаже награды", show_alert=True)

    except Exception as e:
        logger.error(f"Error selling award: {e}")
        await callback.answer("❌ Ошибка при продаже награды", show_alert=True)


@user_leveling_awards_router.callback_query(CancelActivationMenu.filter())
async def cancel_activation_handler(
    callback: CallbackQuery,
    callback_data: CancelActivationMenu,
    user: User,
    stp_repo: MainRequestsRepo,
):
    """
    Хендлер отмены активации награды - меняет статус с "review" обратно на "stored"
    """
    user_award_id = callback_data.user_award_id

    # Получаем информацию о награде
    user_award_detail = await stp_repo.user_award.get_user_award_detail(user_award_id)
    if not user_award_detail:
        await callback.answer("❌ Награда не найдена", show_alert=True)
        return

    user_award = user_award_detail.user_award
    award_info = user_award_detail.award_info

    # Проверяем, что награда на рассмотрении
    if user_award.status != "review":
        await callback.answer(
            "❌ Нельзя отменить активацию этой награды", show_alert=True
        )
        return

    try:
        # Меняем статус обратно на "stored"
        success = await stp_repo.user_award.update_award(
            award_id=user_award_id, status="stored"
        )

        if success:
            await callback.answer(f"✅ Активация награды '{award_info.name}' отменена!")

            logger.info(
                f"[Отмена активации] {user.username} ({user.user_id}) отменил активацию награды '{award_info.name}'"
            )

            # Refresh the award detail view
            await award_detail_view(
                callback, AwardDetailMenu(user_award_id=user_award_id), stp_repo
            )
        else:
            await callback.answer("❌ Ошибка при отмене активации", show_alert=True)

    except Exception as e:
        logger.error(f"Error canceling activation: {e}")
        await callback.answer("❌ Ошибка при отмене активации", show_alert=True)


@user_leveling_awards_router.callback_query(
    LevelingMenu.filter(F.menu == "awards_activation")
)
async def duty_awards_activation(
    callback: CallbackQuery,
    callback_data: DutyActivationListMenu,
    stp_repo: MainRequestsRepo,
    user: User,
):
    """
    Обработчик меню наград для активации дежурными
    Показывает награды со статусом "review" и manager_role == 3
    Фильтрует по division дежурного
    """

    # Достаём номер страницы из callback data, стандартно = 1
    page = getattr(callback_data, "page", 1)

    # Получаем награды ожидающие активации с manager_role == 3 только из того же division что и дежурный
    review_awards = await stp_repo.user_award.get_review_awards_for_activation(
        manager_role=3, division=user.division
    )

    if not review_awards:
        await callback.message.edit_text(
            """<b>✍️ Награды для активации</b>

Нет наград, ожидающих активации 😊""",
            reply_markup=duty_award_activation_kb(page, 0, []),
        )
        return

    # Логика пагинации
    awards_per_page = 5
    total_awards = len(review_awards)
    total_pages = (total_awards + awards_per_page - 1) // awards_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * awards_per_page
    end_idx = start_idx + awards_per_page
    page_awards = review_awards[start_idx:end_idx]

    # Построение списка наград для текущей страницы
    awards_list = []
    for counter, award_detail in enumerate(page_awards, start=start_idx + 1):
        user_award = award_detail.user_award
        award_info = award_detail.award_info

        # Получаем информацию о пользователе
        user = await stp_repo.user.get_user(user_id=user_award.user_id)
        user_name = user.fullname if user else f"ID: {user_award.user_id}"

        if user.username:
            awards_list.append(f"""{counter}. <b>{award_info.name}</b> - {user_award.bought_at.strftime("%d.%m.%Y в %H:%M")}
<blockquote><b>👤 Специалист</b>
<a href='t.me/{user.username}'>{user_name}</a> из {award_info.division}

<b>📝 Описание</b>
{award_info.description}</blockquote>""")
        else:
            awards_list.append(f"""{counter}. <b>{award_info.name}</b> - {user_award.bought_at.strftime("%d.%m.%Y в %H:%M")}
<blockquote><b>👤 Специалист</b>
<a href='tg://user?id={user.user_id}'>{user_name}</a> из {award_info.division}

<b>📝 Описание</b>
{award_info.description}</blockquote>""")
        awards_list.append("")

    message_text = f"""<b>✍️ Награды для активации</b>
<i>Страница {page} из {total_pages}</i>

{chr(10).join(awards_list)}"""

    await callback.message.edit_text(
        message_text,
        reply_markup=duty_award_activation_kb(page, total_pages, page_awards),
    )


@user_leveling_awards_router.callback_query(DutyAwardActivationMenu.filter())
async def duty_award_activation_detail(
    callback: CallbackQuery,
    callback_data: DutyAwardActivationMenu,
    stp_repo: MainRequestsRepo,
):
    """Показывает детальную информацию о награде для активации дежурным"""
    user_award_id = callback_data.user_award_id
    current_page = callback_data.page

    # Получаем информацию о конкретной награде
    user_award_detail = await stp_repo.user_award.get_user_award_detail(user_award_id)

    if not user_award_detail:
        await callback.message.edit_text(
            """<b>✍️ Активация награды</b>

Не смог найти описание для награды ☹""",
            reply_markup=duty_award_detail_kb(user_award_id, current_page),
        )
        return

    user_award = user_award_detail.user_award
    award_info = user_award_detail.award_info

    # Получаем информацию о пользователе
    user: User = await stp_repo.user.get_user(user_id=user_award.user_id)
    user_head: User = await stp_repo.user.get_user(fullname=user.head)

    user_info = (
        f"<a href='t.me/{user.username}'>{user.fullname}</a>"
        if user and user.username
        else "-"
    )
    head_info = (
        f"<a href='t.me/{user_head.username}'>{user.head}</a>"
        if user_head and user_head.username
        else "-"
    )

    message_text = f"""
<b>🎯 Активация награды</b>

<b>🏆 О награде</b>  
<blockquote><b>Название</b>
{award_info.name}

<b>📝 Описание</b>
{award_info.description}

<b>💵 Стоимость</b>
{award_info.cost} баллов

<b>📍 Активаций</b>
{user_award.usage_count} ➡️ {user_award.usage_count + 1} ({award_info.count} всего)</blockquote>"""

    message_text += f"""

<b>👤 О специалисте</b>
<blockquote><b>ФИО</b>
{user_info}

<b>Должность</b>
{user.position} {user.division}

<b>Руководитель</b>
{head_info}</blockquote>

<b>📅 Дата покупки</b>  
{user_award.bought_at.strftime("%d.%m.%Y в %H:%M")}
"""
    await callback.message.edit_text(
        message_text,
        reply_markup=duty_award_detail_kb(user_award_id, current_page),
    )


@user_leveling_awards_router.callback_query(DutyAwardActionMenu.filter())
async def duty_award_action(
    callback: CallbackQuery,
    callback_data: DutyAwardActionMenu,
    stp_repo: MainRequestsRepo,
    user: User,
):
    """Обработка подтверждения/отклонения награды дежурным"""
    user_award_id = callback_data.user_award_id
    action = callback_data.action
    current_page = callback_data.page

    try:
        # Получаем информацию о награде
        user_award_detail = await stp_repo.user_award.get_user_award_detail(
            user_award_id
        )

        if not user_award_detail:
            await callback.answer("❌ Награда не найдена", show_alert=True)
            return

        user_award = user_award_detail.user_award
        award_info = user_award_detail.award_info
        employee_user: User = await stp_repo.user.get_user(user_id=user_award.user_id)

        if action == "approve":
            # Подтверждаем награду
            await stp_repo.user_award.approve_award_usage(
                user_award_id=user_award_id,
                updated_by_user_id=callback.from_user.id,
            )

            await callback.answer(
                f"""✅ Награда '{award_info.name}' активирована!
                
Специалист {employee_user.fullname} был уведомлен об изменении статуса""",
                show_alert=True,
            )

            if user_award.usage_count >= award_info.count:
                employee_notify_message = f"""<b>👌 Награда активирована:</b> {award_info.name}

Дежурный <a href='t.me/{user.username}'>{user.fullname}</a> подтвердил активацию награды

У награды {award_info.name} не осталось использований 

<i>Купить награду повторно можно в меню <b>👏 Награды → ❇️ Доступные</b></i>"""
            else:
                employee_notify_message = f"""<b>👌 Награда активирована:</b> {award_info.name}

Дежурный <a href='t.me/{user.username}'>{user.fullname}</a> подтвердил активацию награды

📍 Осталось активаций: {award_info.count - user_award.usage_count} из {award_info.count}"""

            await callback.bot.send_message(
                chat_id=employee_user.user_id,
                text=employee_notify_message,
            )

            logger.info(
                f"[Дежурный] - [Подтверждение] {callback.from_user.username} ({callback.from_user.id}) подтвердил награду {award_info.name} для пользователя {employee_user.username} ({user_award.user_id})"
            )

        elif action == "reject":
            # Отклоняем награду
            await stp_repo.user_award.reject_award_usage(
                user_award_id=user_award_id, updated_by_user_id=callback.from_user.id
            )

            await callback.answer(
                f"""❌ Награда '{award_info.name}' отклонена

Специалист {employee_user.fullname} был уведомлен об изменении статуса""",
                show_alert=True,
            )

            await callback.bot.send_message(
                chat_id=employee_user.user_id,
                text=f"""<b>Активация отменена:</b> {award_info.name}

Дежурный <a href='t.me/{user.username}'>{user.fullname}</a> отменил активацию награды""",
            )

            logger.info(
                f"[Дежурный] - [Отклонение] {callback.from_user.username} ({callback.from_user.id}) отклонил награду {award_info.name} для пользователя {employee_user.username} ({user_award.user_id})"
            )

        # Возвращаемся к списку наград для активации
        await duty_awards_activation(
            callback=callback,
            callback_data=DutyActivationListMenu(
                menu="duty_activation", page=current_page
            ),
            stp_repo=stp_repo,
            user=user,
        )

    except Exception as e:
        logger.error(f"Error updating award status: {e}")
        await callback.answer("❌ Ошибка при обработке награды", show_alert=True)
