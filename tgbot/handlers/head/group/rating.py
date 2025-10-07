import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from sqlalchemy import Sequence
from tgbot.keyboards.head.group.game.rating import RatingMenu, rating_menu_kb
from tgbot.keyboards.head.group.main import GroupManagementMenu
from tgbot.keyboards.head.group.members import short_name

from infrastructure.database.models import Employee
from infrastructure.database.repo.KPI.requests import KPIRequestsRepo
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import HeadFilter
from tgbot.misc.helpers import format_fullname

head_group_rating_router = Router()
head_group_rating_router.message.filter(F.chat.type == "private", HeadFilter())
head_group_rating_router.callback_query.filter(
    F.message.chat.type == "private", HeadFilter()
)

logger = logging.getLogger(__name__)


def get_kpi_data_by_period(kpi_repo, period: str):
    """Возвращает соответствующий репозиторий KPI в зависимости от периода"""
    period_repos = {
        "day": kpi_repo.spec_day_kpi,
        "week": kpi_repo.spec_week_kpi,
        "month": kpi_repo.spec_month_kpi,
    }
    return period_repos.get(period, kpi_repo.spec_day_kpi)


def get_period_display_text(period: str) -> str:
    """Получает текст для отображения периода с учетом дат"""
    now = datetime.now()

    if period == "day":
        # Показываем вчерашнюю дату
        yesterday = now - timedelta(days=1)
        return f"за {yesterday.strftime('%d.%m')}"

    elif period == "week":
        # Показываем текущую неделю (пн-вс)
        days_since_monday = now.weekday()
        current_monday = now - timedelta(days=days_since_monday)
        current_sunday = current_monday + timedelta(days=6)
        return f"за {current_monday.strftime('%d.%m')} - {current_sunday.strftime('%d.%m')}"

    elif period == "month":
        # Показываем прошлый месяц
        if now.day < 4:
            # Если сегодня меньше 4 числа, показываем позапрошлый месяц
            target_date = now - timedelta(days=now.day + 32)
        else:
            # Показываем прошлый месяц
            if now.month == 1:
                target_date = datetime(now.year - 1, 12, 1)
            else:
                target_date = datetime(now.year, now.month - 1, 1)

        month_names = [
            "январь",
            "февраль",
            "март",
            "апрель",
            "май",
            "июнь",
            "июль",
            "август",
            "сентябрь",
            "октябрь",
            "ноябрь",
            "декабрь",
        ]
        return f"за {month_names[target_date.month - 1]}"

    return ""


def get_latest_update_date(kpi_data: list) -> str:
    """Получает последнюю дату обновления из KPI данных"""
    if not kpi_data:
        return "нет данных"

    # Находим последнюю дату извлечения KPI
    latest_date = None
    for kpi in kpi_data:
        if hasattr(kpi, "kpi_extract_date") and kpi.kpi_extract_date:
            if latest_date is None or kpi.kpi_extract_date > latest_date:
                latest_date = kpi.kpi_extract_date

    if latest_date:
        return latest_date.strftime("%d.%m.%Y %H:%M")
    else:
        return "неизвестно"


def format_target_rating_message(
    group_members: list, premium_data: list, period_data: list, period: str = "day"
) -> str:
    """Форматирует рейтинг по целям (группировка по типам целей)"""
    # Получаем текст периода с датами
    period_display = get_period_display_text(period)

    # Создаем словари данных для быстрого поиска
    premium_dict = {premium.fullname: premium for premium in premium_data}
    period_dict = {kpi.fullname: kpi for kpi in period_data}

    # Группируем сотрудников по типам целей
    target_groups = {}
    for member in group_members:
        premium = premium_dict.get(member.fullname)
        period_kpi = period_dict.get(member.fullname)
        if premium and premium.target_type and period_kpi:
            target_type = premium.target_type

            # Определяем значение цели в зависимости от типа
            if "AHT" in target_type:
                target_value = getattr(period_kpi, "aht", None)
            elif "Продажа" in target_type:
                target_value = getattr(period_kpi, "sales_count", None)
            else:
                target_value = None

            # Добавляем только если есть значение цели и оно не равно 0 или 0.0
            if target_value is not None and target_value != 0 and target_value != 0.0:
                if target_type not in target_groups:
                    target_groups[target_type] = []
                target_groups[target_type].append({
                    "member": member,
                    "premium": premium,
                    "period_kpi": period_kpi,
                    "target_value": target_value,
                })

    if not target_groups:
        return f"""🎖️ <b>Рейтинг группы</b>

🎯 Цель {period_display}

<i>Нет данных о целях</i>

Статистика от: нет данных"""

    message = f"""🎖️ <b>Рейтинг группы</b>

🎯 Цель {period_display}

"""

    # Обрабатываем каждую группу целей
    for target_type, members_data in target_groups.items():
        message += f"<b>{target_type}:</b>\n\n"

        # Определяем логику сортировки
        reverse_sort = "AHT" not in target_type  # Для AHT меньше = лучше

        # Сортируем по значению цели
        members_data.sort(key=lambda x: x["target_value"], reverse=reverse_sort)

        # Ограничиваем до топ-10
        top_members = members_data[:10]

        for i, data in enumerate(top_members, 1):
            member = data["member"]
            period_kpi = data["period_kpi"]

            # Эмодзи для позиций
            if i == 1:
                position_emoji = "🥇"
            elif i == 2:
                position_emoji = "🥈"
            elif i == 3:
                position_emoji = "🥉"
            else:
                position_emoji = f"{i}."

            # Форматируем значение цели в зависимости от типа
            if "AHT" in target_type:
                # Для AHT показываем значение в секундах
                value_str = f"{data['target_value']}"
            elif "Продажа" in target_type:
                # Для продаж показываем sales_count (sales_potential)
                sales_count = data["target_value"]
                sales_potential = getattr(period_kpi, "sales_potential", 0) or 0
                value_str = f"{sales_count} ({sales_potential} потенц.)"
            else:
                value_str = str(int(data["target_value"]))

            # Получаем количество контактов из period_kpi
            contacts_count = getattr(period_kpi, "contacts_count", 0) or 0
            contact_type = "чатов" if member.division == "НЦК" else "звонков"

            message += f"{position_emoji} <b>{
                format_fullname(
                    member.fullname, True, True, member.username, member.user_id
                )
            }</b>\n"
            message += f"{value_str} | {contacts_count} {contact_type}\n"

        message += "\n"  # Разделитель между группами

    # Получаем дату последнего обновления из period_data
    update_date = get_latest_update_date(period_data)
    message += f"\n<i>Статистика от: {update_date}</i>"

    return message


def format_rating_message(
    group_members: Sequence[Employee], kpi_data: list, metric: str, period: str = "day"
) -> str:
    """Форматирует сообщение с рейтингом группы по выбранной метрике и периоду"""
    # Создаем словарь KPI данных для быстрого поиска
    kpi_dict = {kpi.fullname: kpi for kpi in kpi_data}

    # Название метрики для отображения
    metric_names = {
        "csi": "📊 Оценка",
        "pok": "📞 Отклик",
        "flr": "📈 FLR",
        "sales_count": "🎯 Цель",
    }

    metric_title = metric_names.get(metric, "📊 Показатель")

    # Получаем текст периода с датами
    period_display = get_period_display_text(period)

    # Собираем данные для сортировки (только с валидными метриками)
    ratings_data = []

    for member in group_members:
        kpi = kpi_dict.get(member.fullname)
        if kpi:
            value = getattr(kpi, metric, None)
            # Проверяем, что значение существует и не равно 0 или 0.0
            if value is not None and value != 0 and value != 0.0:
                ratings_data.append({"member": member, "value": value, "kpi": kpi})

    # Сортируем по значению метрики (больше = лучше для всех метрик)
    ratings_data.sort(key=lambda x: x["value"], reverse=True)

    # Ограничиваем до топ-10
    ratings_data = ratings_data[:10]

    # Формируем сообщение
    message = f"""🎖️ <b>Рейтинг группы</b>

{metric_title} {period_display}

"""

    for i, data in enumerate(ratings_data, 1):
        member = data["member"]
        value = data["value"]
        kpi = data["kpi"]

        # Эмодзи для позиций
        if i == 1:
            position_emoji = "🥇"
        elif i == 2:
            position_emoji = "🥈"
        elif i == 3:
            position_emoji = "🥉"
        else:
            position_emoji = f"{i}."

        # Форматируем значение метрики
        if metric in ["csi", "pok", "flr"]:
            value_str = f"{value:.2f}"
        else:
            value_str = str(int(value))

        # Получаем количество контактов для отображения
        contacts_count = getattr(kpi, "contacts_count", 0) or 0

        # Определяем тип контактов по подразделению
        contact_type = "чатов" if member.division == "НЦК" else "звонков"

        message += f"{position_emoji} <b><a href='t.me/{member.username}'>{short_name(member.fullname)}</a></b>\n"
        message += f"{value_str} | {contacts_count} {contact_type}\n"

    if not ratings_data:
        message += "<i>Нет данных за выбранный период</i>\n\n"

    # Получаем дату последнего обновления
    update_date = get_latest_update_date([
        item["kpi"] for item in ratings_data if item["kpi"]
    ])
    message += f"\n<i>Статистика от: {update_date}</i>"

    return message


@head_group_rating_router.callback_query(GroupManagementMenu.filter(F.menu == "rating"))
async def group_rating_cb(
    callback: CallbackQuery,
    user: Employee,
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
):
    """Обработчик рейтинга группы - показывает меню выбора метрики"""
    if not user:
        await callback.message.edit_text(
            """❌ <b>Ошибка</b>

Не удалось найти информацию в базе данных."""
        )
        return

    # Получаем всех сотрудников этого руководителя
    group_members = await stp_repo.employee.get_users_by_head(user.fullname)

    if not group_members:
        await callback.message.edit_text(
            """🎖️ <b>Рейтинг группы</b>

У тебя пока нет подчиненных в системе

<i>Если это ошибка, обратись к администратору.</i>""",
            reply_markup=rating_menu_kb("day", "csi"),
        )
        return

    # По умолчанию показываем рейтинг по оценке (CSI) за день
    fullnames = [member.fullname for member in group_members]
    kpi_repo_day = get_kpi_data_by_period(kpi_repo, "day")
    kpi_data = await kpi_repo_day.get_kpi_by_names(fullnames)
    message_text = format_rating_message(group_members, kpi_data, "csi", "day")

    await callback.message.edit_text(
        message_text,
        reply_markup=rating_menu_kb("day", "csi"),
    )


@head_group_rating_router.callback_query(RatingMenu.filter())
async def rating_metric_cb(
    callback: CallbackQuery,
    callback_data: RatingMenu,
    user: Employee,
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
):
    """Обработчик выбора метрики и периода для рейтинга"""
    metric = callback_data.metric
    period = callback_data.period

    if not user:
        await callback.answer("❌ Ошибка получения данных", show_alert=True)
        return

    # Получаем всех сотрудников этого руководителя
    group_members = await stp_repo.employee.get_users_by_head(user.fullname)

    if not group_members:
        await callback.answer("❌ Участники не найдены", show_alert=True)
        return

    try:
        fullnames = [member.fullname for member in group_members]

        if metric == "sales_count":
            # Особая логика для целей - получаем target_type из premium, а данные из period-specific таблицы
            premium_data = await kpi_repo.spec_premium.get_kpi_by_names(fullnames)
            kpi_repo_period = get_kpi_data_by_period(kpi_repo, period)
            period_data = await kpi_repo_period.get_kpi_by_names(fullnames)
            message_text = format_target_rating_message(
                group_members, premium_data, period_data, period
            )
        else:
            # Обычная логика для остальных метрик
            kpi_repo_period = get_kpi_data_by_period(kpi_repo, period)
            kpi_data = await kpi_repo_period.get_kpi_by_names(fullnames)
            message_text = format_rating_message(
                group_members, kpi_data, metric, period
            )

        try:
            await callback.message.edit_text(
                message_text,
                reply_markup=rating_menu_kb(period, metric),
            )
        except TelegramBadRequest:
            await callback.answer("Обновлений нет")

    except Exception as e:
        logger.error(
            f"Ошибка при получении рейтинга по метрике {metric} за период {period}: {e}"
        )
        await callback.answer(
            "❌ Ошибка при получении данных рейтинга", show_alert=True
        )
