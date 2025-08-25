import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.keyboards.mip.leveling.main import LevelingMenu
from tgbot.keyboards.user.leveling.awards import (
    AwardDetailMenu,
    AwardHistoryMenu,
    AwardPurchaseConfirmMenu,
    AwardPurchaseMenu,
    AwardsMenu,
    UseAwardMenu,
    available_awards_paginated_kb,
    award_confirmation_kb,
    award_detail_back_kb,
    award_detail_kb,
    award_history_kb,
    awards_kb,
    awards_paginated_kb,
    to_awards_kb,
)
from tgbot.misc.dicts import executed_codes


def get_status_emoji(status: str) -> str:
    """Возвращает эмодзи в зависимости от статуса"""
    status_emojis = {
        "stored": "📦",
        "waiting": "⏳",
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


@user_leveling_awards_router.callback_query(LevelingMenu.filter(F.menu == "awards"))
async def user_awards_cb(callback: CallbackQuery):
    await callback.message.edit_text(
        """<b>👏 Награды</b>

Здесь ты можешь найти доступные для приобретения, а так же все возможные награды""",
        reply_markup=awards_kb(),
    )


@user_leveling_awards_router.callback_query(AwardsMenu.filter(F.menu == "all"))
async def awards_all(
    callback: CallbackQuery,
    user: User,
    callback_data: AwardsMenu,
    stp_repo: RequestsRepo,
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
    stp_repo: RequestsRepo,
):
    """
    Обработчик клика на меню доступных для покупки наград
    """

    # Достаём номер страницы из callback data, стандартно = 1
    page = getattr(callback_data, "page", 1)

    # Получаем баланс пользователя (заработанные - потраченные баллы)
    achievements_sum = await stp_repo.user_achievement.get_user_achievements_sum(
        user_id=user.user_id
    )
    awards_sum = await stp_repo.user_award.get_user_awards_sum(user_id=user.user_id)
    user_balance = achievements_sum - awards_sum

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

<b>💰 Твой баланс:</b> {user_balance} баллов
<i>Страница {page} из {total_pages}</i>

{"\n".join(awards_list)}"""

    await callback.message.edit_text(
        message_text,
        reply_markup=available_awards_paginated_kb(page, total_pages, page_awards),
    )
    logger.info(
        f"[Пользователь] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыто меню доступных наград, страница {page}, баланс: {user_balance}"
    )


@user_leveling_awards_router.callback_query(AwardsMenu.filter(F.menu == "executed"))
async def awards_history(callback: CallbackQuery, stp_repo: RequestsRepo):
    """Показывает историю наград пользователя в виде клавиатуры с пагинацией"""
    user_awards_with_details = await stp_repo.user_award.get_user_awards_with_details(
        user_id=callback.from_user.id
    )

    if not user_awards_with_details:
        await callback.message.edit_text(
            """<b>✴️ Купленные награды</b>

Здесь ты найдешь все приобретенные награды, а так же их статус и многое другое

У тебя пока нет использованных наград 🙂""",
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
    callback: CallbackQuery, callback_data: AwardHistoryMenu, stp_repo: RequestsRepo
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
    callback: CallbackQuery, callback_data: AwardDetailMenu, stp_repo: RequestsRepo
):
    """Показывает детальную информацию о конкретной награде"""
    user_award_id = callback_data.user_award_id

    # Получаем информацию о конкретной награде
    user_award_detail = await stp_repo.user_award.get_user_award_detail(user_award_id)

    if not user_award_detail:
        await callback.message.edit_text(
            """<b>🏆 Просмотр награды</b>

Не смог найти описание для награды ☹""",
            reply_markup=award_detail_back_kb(),
        )
        return

    user_award = user_award_detail.user_award
    award_info = user_award_detail.award_info

    # Получаем эмодзи и название статуса
    status_names = {
        "stored": "Готова к использованию",
        "waiting": "На проверке",
        "used_up": "Полностью использована",
        "canceled": "Отменена",
        "rejected": "Отклонена",
    }
    status_name = status_names.get(user_award.status, "Неизвестный статус")

    # Проверяем, можно ли использовать награду
    can_use = (
        user_award.status == "stored"
        and user_award_detail.current_usages < user_award_detail.max_usages
    )

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
        message_text += (
            f"\n\n<blockquote expandable><b>👤 Ответственный</b>\n<a href='tg://user?id={manager.user_id}'>"
            f"{manager.fullname}</a>"
        )
        message_text += f"\n\n<b>📅 Дата проверки ответственным</b>\n{user_award.updated_at.strftime('%d.%m.%Y в %H:%M')}</blockquote>"

    # Use the new keyboard with "Use Award" button if award can be used
    keyboard = (
        award_detail_kb(user_award.id, can_use=can_use)
        if can_use
        else award_detail_back_kb()
    )
    await callback.message.edit_text(message_text, reply_markup=keyboard)


@user_leveling_awards_router.callback_query(AwardPurchaseMenu.filter())
async def award_confirmation_handler(
    callback: CallbackQuery,
    callback_data: AwardPurchaseMenu,
    user: User,
    stp_repo: RequestsRepo,
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
    achievements_sum = await stp_repo.user_achievement.get_user_achievements_sum(
        user_id=user.user_id
    )
    awards_sum = await stp_repo.user_award.get_user_awards_sum(user_id=user.user_id)
    user_balance = achievements_sum - awards_sum

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
    message_text = f"""<b>🎯 Подтверждение покупки</b>

<b>🏆 Награда</b>
{award_info.name}

<b>📝 Описание</b>
{award_info.description}

<b>💵 Стоимость</b>
{award_info.cost} баллов"""

    if award_info.count > 1:
        message_text += f"\n<b>📍 Количество использований:</b> {award_info.count}"

    message_text += f"""

<b>💰 Баланс</b>
• Текущий: {user_balance} баллов
• После покупки: {balance_after_purchase} баллов

<i>После приобретения награда будет доступна в меню купленных наград</i>"""

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
    stp_repo: RequestsRepo,
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

        # Проверяем баланс еще раз (на случай изменений)
        achievements_sum = await stp_repo.user_achievement.get_user_achievements_sum(
            user_id=user.user_id
        )
        awards_sum = await stp_repo.user_award.get_user_awards_sum(user_id=user.user_id)
        user_balance = achievements_sum - awards_sum

        if user_balance < award_info.cost:
            await callback.answer(
                f"❌ Недостаточно баллов! У тебя: {user_balance}, нужно: {award_info.cost}",
                show_alert=True,
            )
            return

        # Создаем награду пользователю с новым статусом "stored"
        try:
            await stp_repo.user_award.create_user_award(
                user_id=user.user_id, award_id=award_id, status="stored"
            )

            await callback.answer(
                f"✅ Награда '{award_info.name}' успешно приобретена!\n\n"
                f"📦 Статус: Готова к использованию\n"
                f"💰 Списано: {award_info.cost} баллов\n\n"
                f"🎯 Найди её в разделе 'Купленные награды' и нажми 'Использовать' когда будешь готов",
                show_alert=True,
            )

            logger.info(
                f"[Покупка награды] {callback.from_user.username} ({user.user_id}) купил награду '{award_info.name}' за {award_info.cost} баллов со статусом 'stored'"
            )

            # Возвращаемся к списку доступных наград
            await awards_available(
                callback=callback,
                user=user,
                callback_data=AwardsMenu(menu="available", page=current_page),
                stp_repo=stp_repo,
            )

        except Exception as e:
            logger.error(f"Error creating user award: {e}")
            await callback.answer("❌ Ошибка при покупке награды", show_alert=True)


@user_leveling_awards_router.callback_query(UseAwardMenu.filter())
async def use_award_handler(
    callback: CallbackQuery,
    callback_data: UseAwardMenu,
    user: User,
    stp_repo: RequestsRepo,
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

        logger.info(
            f"[Использование награды] {user.username} ({user.user_id}) отправил на рассмотрение награду '{award_name}'"
        )
    else:
        await callback.answer("❌ Невозможно использовать награду", show_alert=True)

    # Refresh the award detail view
    await award_detail_view(
        callback, AwardDetailMenu(user_award_id=user_award_id), stp_repo
    )
