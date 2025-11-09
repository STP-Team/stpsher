"""Обработчики событий рассылок."""

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, ManagedMultiselect, Radio, Select
from sqlalchemy import select
from stp_database import Employee, MainRequestsRepo

from tgbot.dialogs.states.common.broadcast import Broadcast
from tgbot.misc.dicts import roles
from tgbot.services.broadcaster import broadcast_copy


async def start_broadcast_dialog(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик перехода в диалог рассылок.

    Args:
        _event: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(
        Broadcast.menu,
    )


async def on_broadcast_message_during_progress(
    _message: Message,
    _widget: MessageInput,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик сообщений от пользователя во время рассылки.

    Устанавливает режим EDIT, чтобы предотвратить создание новых сообщений
    и заставить бот редактировать существующее сообщение вместо отправки нового.

    Args:
        _message: Сообщение от пользователя
        _widget: Виджет ввода сообщения
        dialog_manager: Менеджер диалога
    """
    dialog_manager.show_mode = ShowMode.EDIT


async def on_broadcast_type_selected(
    _event: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик выбора типа рассылки.

    Args:
        _event: Callback query от пользователя
        _widget: Select виджет
        dialog_manager: Менеджер диалога
        item_id: Идентификатор типа рассылки
    """
    # Очищаем предыдущие выборы при смене типа рассылки
    if "broadcast_items" in dialog_manager.dialog_data:
        del dialog_manager.dialog_data["broadcast_items"]
    if "broadcast_filter" in dialog_manager.dialog_data:
        del dialog_manager.dialog_data["broadcast_filter"]

    dialog_manager.dialog_data["broadcast_type"] = item_id

    # Если выбран тип "all", пропускаем выбор и переходим сразу к вводу текста
    if item_id == "all":
        await dialog_manager.switch_to(Broadcast.new_broadcast_text)
    else:
        # Для "by_division" и "by_group" переходим к выбору элементов
        await dialog_manager.switch_to(Broadcast.new_broadcast_select)

        # Очищаем состояние multiselect виджета после переключения
        try:
            multiselect: ManagedMultiselect = dialog_manager.find("items_multiselect")
            # Снимаем все отметки с элементов
            for item_id_checked in list(multiselect.get_checked()):
                await multiselect.set_checked(item_id_checked, False)
        except Exception:
            # Виджет может быть еще не инициализирован, игнорируем
            pass


async def on_broadcast_filter_changed(
    _event: CallbackQuery,
    _widget: Radio,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик изменения фильтра направлений.

    Args:
        _event: Callback query от пользователя
        _widget: Radio виджет
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранного фильтра
    """
    dialog_manager.dialog_data["broadcast_filter"] = item_id


async def on_broadcast_items_confirmed(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик подтверждения выбора направлений/групп.

    Args:
        _event: Callback query от пользователя
        _widget: Button виджет
        dialog_manager: Менеджер диалога
    """
    multiselect: ManagedMultiselect = dialog_manager.find("items_multiselect")
    selected_items = multiselect.get_checked()

    # Сохраняем выбранные элементы
    dialog_manager.dialog_data["broadcast_items"] = list(selected_items)

    await dialog_manager.switch_to(Broadcast.new_broadcast_text)


async def on_broadcast_text_input(
    message: Message,
    _widget: MessageInput,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик ввода текста рассылки.

    Args:
        message: Сообщение от пользователя
        _widget: Виджет ввода сообщения
        dialog_manager: Менеджер диалога
    """
    if len(message.text) > 4096:
        await message.answer(
            "Слишком длинное сообщение. Максимальное кол-во символов - 4096"
        )
        return
    dialog_manager.dialog_data["broadcast_text"] = message.html_text
    dialog_manager.dialog_data["broadcast_message_id"] = message.message_id
    dialog_manager.dialog_data["broadcast_from_chat_id"] = message.chat.id
    await dialog_manager.switch_to(Broadcast.new_broadcast_check)


async def on_broadcast_send(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик отправки рассылки.

    Args:
        _event: Callback query от пользователя
        _widget: Button виджет
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    bot: Bot = dialog_manager.middleware_data["bot"]

    broadcast_type = dialog_manager.dialog_data.get("broadcast_type")
    broadcast_items = dialog_manager.dialog_data.get("broadcast_items", [])
    message_id = dialog_manager.dialog_data.get("broadcast_message_id")
    from_chat_id = dialog_manager.dialog_data.get("broadcast_from_chat_id")

    # Получаем список user_ids для рассылки
    user_ids = []

    if broadcast_type == "all":
        # Получить всех пользователей
        employees = await stp_repo.employee.get_users()
        user_ids = [emp.user_id for emp in employees if emp.user_id]

    elif broadcast_type == "by_division":
        # Получить пользователей по направлениям
        for division in broadcast_items:
            query = select(Employee).where(Employee.division == division)
            result = await stp_repo.session.execute(query)
            employees = result.scalars().all()
            user_ids.extend([emp.user_id for emp in employees if emp.user_id])

    elif broadcast_type == "by_group":
        # Получить пользователей по руководителям
        for head_id in broadcast_items:
            # Получаем руководителя по ID
            head = await stp_repo.employee.get_users(main_id=int(head_id))
            if head:
                # Получаем сотрудников этого руководителя
                employees = await stp_repo.employee.get_users(head=head.fullname)
                user_ids.extend([emp.user_id for emp in employees if emp.user_id])

    elif broadcast_type == "by_role":
        # Получить пользователей по ролям
        role_ids = [int(role_id) for role_id in broadcast_items]
        employees = await stp_repo.employee.get_users(roles=role_ids)
        user_ids = [emp.user_id for emp in employees if emp.user_id]

    # Сохраняем данные для progress и result
    dialog_manager.dialog_data["user_ids"] = user_ids
    dialog_manager.dialog_data["total_users"] = len(user_ids)
    dialog_manager.dialog_data["current_progress"] = 0

    # Переходим к окну прогресса
    await dialog_manager.switch_to(Broadcast.new_broadcast_progress)

    # Callback для обновления прогресса
    async def update_progress(current: int, total: int) -> None:
        dialog_manager.dialog_data["current_progress"] = current
        await dialog_manager.update({})

    success_count, error_count = await broadcast_copy(
        bot=bot,
        users=user_ids,
        from_chat_id=from_chat_id,
        message_id=message_id,
        disable_notification=False,
        progress_callback=update_progress,
    )

    # Сохраняем результаты
    dialog_manager.dialog_data["success_count"] = success_count
    dialog_manager.dialog_data["error_count"] = error_count

    # Сохраняем рассылку в базу данных
    user_id = _event.from_user.id
    broadcast_text = dialog_manager.dialog_data.get("broadcast_text")

    db_type = ""
    target = ""

    # Определяем тип и цель для сохранения в БД
    if broadcast_type == "all":
        db_type = "division"
        target = "all"
    elif broadcast_type == "by_division":
        db_type = "division"
        target = ", ".join(broadcast_items)
    elif broadcast_type == "by_group":
        db_type = "group"
        # Получаем ФИО руководителей для target
        head_names = []
        for head_id in broadcast_items:
            head = await stp_repo.employee.get_users(main_id=int(head_id))
            if head:
                head_names.append(head.fullname)
        target = ", ".join(head_names)
    elif broadcast_type == "by_role":
        db_type = "role"
        # Получаем названия ролей для target
        role_names = []
        for role_id in broadcast_items:
            role_data = roles.get(int(role_id))
            if role_data:
                role_names.append(role_data["name"])
        target = ", ".join(role_names)

    # Создаем запись о рассылке
    await stp_repo.broadcast.create_broadcast(
        user_id=user_id,
        broadcast_type=db_type,
        target=target,
        text=broadcast_text,
        recipients=user_ids,
    )

    # Переходим к окну результатов
    await dialog_manager.switch_to(Broadcast.new_broadcast_result)


async def on_broadcast_back_to_menu(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик возврата в главное меню рассылок с очисткой данных.

    Args:
        _event: Callback query от пользователя
        _widget: Button виджет
        dialog_manager: Менеджер диалога
    """
    # Очищаем все данные диалога
    dialog_manager.dialog_data.clear()
    await dialog_manager.switch_to(Broadcast.menu)


async def on_broadcast_history_item_selected(
    _event: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик выбора рассылки из истории для просмотра деталей.

    Args:
        _event: Callback query от пользователя
        _widget: Select виджет
        dialog_manager: Менеджер диалога
        item_id: ID выбранной рассылки
    """
    dialog_manager.dialog_data["selected_broadcast_id"] = int(item_id)
    await dialog_manager.switch_to(Broadcast.history_detail)


async def on_broadcast_resend(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик повторной отправки рассылки.

    Args:
        _event: Callback query от пользователя
        _widget: Button виджет
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    bot: Bot = dialog_manager.middleware_data["bot"]

    broadcast_id = dialog_manager.dialog_data.get("selected_broadcast_id")
    broadcast = await stp_repo.broadcast.get_broadcasts(broadcast_id)

    if not broadcast:
        return

    # Получаем список получателей
    user_ids = broadcast.recipients or []

    # Сохраняем данные для progress и result
    dialog_manager.dialog_data["user_ids"] = user_ids
    dialog_manager.dialog_data["total_users"] = len(user_ids)
    dialog_manager.dialog_data["current_progress"] = 0
    dialog_manager.dialog_data["broadcast_text"] = broadcast.text

    # Переходим к окну прогресса
    await dialog_manager.switch_to(Broadcast.new_broadcast_progress)

    # Callback для обновления прогресса
    async def update_progress(current: int, total: int) -> None:
        dialog_manager.dialog_data["current_progress"] = current
        await dialog_manager.update({})

    success_count, error_count = await broadcast_copy(
        bot=bot,
        users=user_ids,
        text=broadcast.text,
        disable_notification=False,
        progress_callback=update_progress,
    )

    # Сохраняем результаты
    dialog_manager.dialog_data["success_count"] = success_count
    dialog_manager.dialog_data["error_count"] = error_count

    # Сохраняем новую рассылку в базу данных
    user_id = _event.from_user.id
    await stp_repo.broadcast.create_broadcast(
        user_id=user_id,
        broadcast_type=broadcast.type,
        target=broadcast.target,
        text=broadcast.text,
        recipients=user_ids,
    )

    # Переходим к окну результатов
    await dialog_manager.switch_to(Broadcast.new_broadcast_result)
