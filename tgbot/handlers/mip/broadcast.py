import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PhotoSize

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.broadcast import (
    BroadcastMenu,
    broadcast_kb,
    broadcast_type_kb,
    confirmation_kb,
    division_selection_kb,
    heads_selection_kb,
)
from tgbot.keyboards.user.main import MainMenu
from tgbot.misc.states.mip.broadcast import BroadcastState
from tgbot.services.broadcaster import send_message

mip_broadcast_router = Router()
mip_broadcast_router.message.filter(F.chat.type == "private", MipFilter())
mip_broadcast_router.callback_query.filter(
    F.message.chat.type == "private", MipFilter()
)

logger = logging.getLogger(__name__)


@mip_broadcast_router.callback_query(MainMenu.filter(F.menu == "broadcast"))
async def mip_broadcast_cmd(callback: CallbackQuery, state: FSMContext):
    """Главное меню рассылки"""
    await state.clear()
    await callback.message.edit_text(
        """<b>📢 Рассылка</b>

Здесь ты можешь запустить рассылку сообщений по направлению

Отправь сообщение для рассылки:
• Текстовое сообщение
• Сообщение с фото

<i>После отправки ты сможешь выбрать получателей</i>""",
        reply_markup=broadcast_kb(),
    )
    await state.set_state(BroadcastState.waiting_message)


@mip_broadcast_router.message(BroadcastState.waiting_message, F.text)
async def process_text_message(message: Message, state: FSMContext):
    """Обработка текстового сообщения"""
    await state.update_data(
        message_text=message.text, 
        message_type="text", 
        original_message_id=message.message_id,
        original_chat_id=message.chat.id
    )

    # Показать выбор типа рассылки
    await show_broadcast_type_selection(message, state)


@mip_broadcast_router.message(BroadcastState.waiting_message, F.photo)
async def process_photo_message(message: Message, state: FSMContext):
    """Обработка сообщения с фото"""
    caption = message.caption or ""

    await state.update_data(
        message_text=caption, 
        message_type="photo", 
        original_message_id=message.message_id,
        original_chat_id=message.chat.id
    )

    # Показать выбор типа рассылки
    await show_broadcast_type_selection(message, state)


async def show_broadcast_type_selection(message: Message, state: FSMContext):
    """Показать выбор типа рассылки"""
    data = await state.get_data()
    message_preview = data.get("message_text", "")
    if len(message_preview) > 100:
        message_preview = message_preview[:100] + "..."

    has_photo = data.get("message_type") == "photo"
    photo_text = "\n📸 С фото" if has_photo else ""

    bot_message = await message.bot.send_message(
        chat_id=message.chat.id,
        text=f"""<b>📢 Рассылка готова!</b>

<b>Сообщение:</b>
{message_preview}{photo_text}

<b>Выбери получателей:</b>""",
        reply_markup=broadcast_type_kb(),
    )

    await state.update_data(bot_message_id=bot_message.message_id)
    await state.set_state(BroadcastState.selecting_type)


@mip_broadcast_router.callback_query(
    BroadcastState.selecting_type, BroadcastMenu.filter(F.action == "everyone")
)
async def broadcast_everyone(
    callback: CallbackQuery, state: FSMContext, stp_repo: MainRequestsRepo
):
    """Рассылка всем"""
    data = await state.get_data()

    # Получаем всех пользователей
    all_users = await stp_repo.user.get_users()
    user_count = len(all_users)

    message_preview = data.get("message_text", "")
    if len(message_preview) > 150:
        message_preview = message_preview[:150] + "..."

    has_photo = data.get("message_type") == "photo"
    photo_text = "\n📸 С фото" if has_photo else ""

    await callback.message.edit_text(
        f"""<b>📢 Подтверждение рассылки</b>

<b>Получатели:</b> Все пользователи ({user_count} чел.)

<b>Сообщение:</b>
{message_preview}{photo_text}

<b>⚠️ Рассылка будет отправлена всем пользователям!</b>""",
        reply_markup=confirmation_kb(),
    )

    await state.update_data(
        recipients="everyone",
        recipient_ids=[user.user_id for user in all_users],
        user_count=user_count,
    )


@mip_broadcast_router.callback_query(
    BroadcastState.selecting_type, BroadcastMenu.filter(F.action == "division")
)
async def select_division(callback: CallbackQuery):
    """Выбор подразделения"""
    await callback.message.edit_text(
        """<b>📢 Выбор подразделения</b>

Выбери подразделение для рассылки:""",
        reply_markup=division_selection_kb(),
    )


@mip_broadcast_router.callback_query(
    BroadcastState.selecting_type,
    BroadcastMenu.filter(F.action.in_(["ntp1", "ntp2", "nck"])),
)
async def broadcast_division(
    callback: CallbackQuery,
    callback_data: BroadcastMenu,
    state: FSMContext,
    stp_repo: MainRequestsRepo,
):
    """Рассылка по подразделению"""
    division_code = callback_data.action.upper()  # "NTP" or "NCK"
    division_name = ""
    match division_code:
        case "NTP1":
            division_name = "НТП1"
        case "NTP2":
            division_name = "НТП2"
        case "NCK":
            division_name = "НЦК"
        case _:
            division_name = "НЦК"

    # Получаем пользователей подразделения
    all_users = await stp_repo.user.get_users()
    division_users = [
        user for user in all_users if user.division == division_name and user.user_id
    ]
    user_count = len(division_users)

    if not division_users:
        await callback.answer(
            f"❌ Пользователи {division_name} не найдены", show_alert=True
        )
        return

    data = await state.get_data()
    message_preview = data.get("message_text", "")
    if len(message_preview) > 150:
        message_preview = message_preview[:150] + "..."

    has_photo = data.get("message_type") == "photo"
    photo_text = "\n📸 С фото" if has_photo else ""

    await callback.message.edit_text(
        f"""<b>📢 Подтверждение рассылки</b>

<b>Получатели:</b> {division_name} ({user_count} чел.)

<b>Сообщение:</b>
{message_preview}{photo_text}

<b>⚠️ Рассылка будет отправлена всем сотрудникам {division_name}!</b>""",
        reply_markup=confirmation_kb(),
    )

    await state.update_data(
        recipients=division_code.lower(),
        recipient_ids=[user.user_id for user in division_users],
        user_count=user_count,
        division_name=division_name,
    )


@mip_broadcast_router.callback_query(
    BroadcastState.selecting_type, BroadcastMenu.filter(F.action == "groups")
)
async def select_heads(
    callback: CallbackQuery, state: FSMContext, stp_repo: MainRequestsRepo
):
    """Выбор руководителей для рассылки по группам"""
    # Получаем всех руководителей
    all_users = await stp_repo.user.get_users()
    heads = [user for user in all_users if user.role == 2]  # role 2 = head

    if not heads:
        await callback.answer("❌ Руководители не найдены", show_alert=True)
        return

    # Сортируем по ФИО
    heads.sort(key=lambda x: x.fullname)

    await callback.message.edit_text(
        f"""<b>📢 Выбор групп</b>

Найдено руководителей: {len(heads)}
Выбери руководителей для рассылки их группам:

<i>💡 Можно выбрать несколько групп</i>""",
        reply_markup=heads_selection_kb(
            [(head.fullname, head.user_id) for head in heads]
        ),
    )

    await state.update_data(
        available_heads=[(head.fullname, head.user_id) for head in heads],
        selected_heads=[],
    )


@mip_broadcast_router.callback_query(
    BroadcastState.selecting_type,
    BroadcastMenu.filter(F.action.startswith("toggle_head_")),
)
async def toggle_head_selection(
    callback: CallbackQuery,
    callback_data: BroadcastMenu,
    state: FSMContext,
):
    """Переключить выбор руководителя"""
    head_id = int(callback_data.action.replace("toggle_head_", ""))

    data = await state.get_data()
    selected_heads = data.get("selected_heads", [])
    available_heads = data.get("available_heads", [])

    # Находим руководителя
    head_info = next((head for head in available_heads if head[1] == head_id), None)
    if not head_info:
        await callback.answer("❌ Руководитель не найден", show_alert=True)
        return

    # Переключаем выбор
    if head_id in selected_heads:
        selected_heads.remove(head_id)
    else:
        selected_heads.append(head_id)

    await state.update_data(selected_heads=selected_heads)

    # Обновляем клавиатуру
    heads = [head for head in available_heads]
    await callback.message.edit_reply_markup(
        reply_markup=heads_selection_kb(
            [(name, uid) for name, uid in heads], selected_heads
        )
    )


@mip_broadcast_router.callback_query(
    BroadcastState.selecting_type, BroadcastMenu.filter(F.action == "confirm_heads")
)
async def confirm_heads_selection(
    callback: CallbackQuery, state: FSMContext, stp_repo: MainRequestsRepo
):
    """Подтвердить выбор руководителей"""
    data = await state.get_data()
    selected_heads = data.get("selected_heads", [])
    available_heads = data.get("available_heads", [])

    if not selected_heads:
        await callback.answer("❌ Выбери хотя бы одного руководителя", show_alert=True)
        return

    # Получаем информацию о выбранных руководителях
    selected_head_names = []
    all_group_users = []

    for head_id in selected_heads:
        head_info = next((head for head in available_heads if head[1] == head_id), None)
        if head_info:
            head_name = head_info[0]
            selected_head_names.append(head_name)

            # Получаем сотрудников группы
            group_users = await stp_repo.user.get_users_by_head(head_name)
            all_group_users.extend(group_users)

    # Убираем дубликаты пользователей
    unique_users = list(
        {user.user_id: user for user in all_group_users if user.user_id}.values()
    )
    user_count = len(unique_users)

    if user_count == 0:
        await callback.answer(
            "❌ В выбранных группах нет пользователей", show_alert=True
        )
        return

    message_preview = data.get("message_text", "")
    if len(message_preview) > 150:
        message_preview = message_preview[:150] + "..."

    has_photo = data.get("message_type") == "photo"
    photo_text = "\n📸 С фото" if has_photo else ""

    heads_list = "\n".join([f"• {name}" for name in selected_head_names])

    await callback.message.edit_text(
        f"""<b>📢 Подтверждение рассылки</b>

<b>Получатели:</b> Группы руководителей ({user_count} чел.)

<b>Выбранные руководители:</b>
{heads_list}

<b>Сообщение:</b>
{message_preview}{photo_text}

<b>⚠️ Рассылка будет отправлена всем сотрудникам выбранных групп!</b>""",
        reply_markup=confirmation_kb(),
    )

    await state.update_data(
        recipients="groups",
        recipient_ids=[user.user_id for user in unique_users],
        user_count=user_count,
        selected_head_names=selected_head_names,
    )


@mip_broadcast_router.callback_query(
    BroadcastState.selecting_type, BroadcastMenu.filter(F.action == "confirm")
)
async def start_broadcast(
    callback: CallbackQuery, state: FSMContext, bot: Bot, stp_repo: MainRequestsRepo
):
    """Начать рассылку"""
    data = await state.get_data()

    message_text = data.get("message_text", "")
    message_type = data.get("message_type", "text")
    original_message_id = data.get("original_message_id")
    original_chat_id = data.get("original_chat_id")
    recipient_ids = data.get("recipient_ids", [])
    user_count = data.get("user_count", 0)
    recipients = data.get("recipients", "")

    if not recipient_ids:
        await callback.answer("❌ Список получателей пуст", show_alert=True)
        return

    # Определяем тип и цель рассылки для сохранения в БД
    broadcast_type = "division"
    broadcast_target = ""

    if recipients == "everyone":
        broadcast_type = "division"
        broadcast_target = "all"
    elif recipients in ["ntp1", "ntp2", "nck"]:
        broadcast_type = "division"
        broadcast_target = data.get("division_name", recipients.upper())
    elif recipients == "groups":
        broadcast_type = "group"
        selected_head_names = data.get("selected_head_names", [])
        broadcast_target = ", ".join(selected_head_names)

    # Сохраняем рассылку в БД
    try:
        saved_broadcast = await stp_repo.broadcast.create_broadcast(
            user_id=callback.from_user.id,
            type=broadcast_type,
            target=broadcast_target,
            text=message_text,
            recipients=recipient_ids,
        )
        if saved_broadcast:
            logger.info(f"Рассылка сохранена в БД с ID: {saved_broadcast.id}")
        else:
            logger.warning("Не удалось сохранить рассылку в БД")
    except Exception as e:
        logger.error(f"Ошибка сохранения рассылки в БД: {e}")
        # Продолжаем выполнение рассылки даже если не удалось сохранить в БД

    # Показываем прогресс
    progress_message = await callback.message.edit_text(
        f"""<b>📤 Рассылка запущена!</b>

<b>Получателей:</b> {user_count}
<b>Отправлено:</b> 0 / {user_count}
<b>Статус:</b> Отправка...

<i>⏳ Не закрывайте бота до завершения</i>""",
        reply_markup=None,
    )

    # Запускаем рассылку
    success_count = 0

    try:
        for i, user_id in enumerate(recipient_ids, 1):
            try:
                # Используем copy_message для сохранения оригинального форматирования
                await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=original_chat_id,
                    message_id=original_message_id
                )
                success_count += 1

                # Обновляем прогресс каждые 10 сообщений
                if i % 10 == 0 or i == len(recipient_ids):
                    await progress_message.edit_text(
                        f"""<b>📤 Рассылка в процессе</b>

<b>Получателей:</b> {user_count}
<b>Отправлено:</b> {i} / {user_count}
<b>Успешно:</b> {success_count}
<b>Прогресс:</b> {(i / len(recipient_ids) * 100):.1f}%

<i>⏳ Не закрывайте бота до завершения</i>"""
                    )

                # Задержка между отправками
                await asyncio.sleep(0.05)  # 20 сообщений в секунду

            except Exception as e:
                logger.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
                continue

    except Exception as e:
        logger.error(f"Ошибка во время рассылки: {e}")
        await progress_message.edit_text(
            f"""<b>❌ Ошибка рассылки</b>

Произошла ошибка во время рассылки.
Отправлено: {success_count} из {user_count} сообщений""",
            reply_markup=broadcast_kb(),
        )
        await state.clear()
        return

    # Показываем результат
    success_rate = (success_count / user_count * 100) if user_count > 0 else 0

    recipient_type_text = {
        "everyone": "всем пользователям",
        "ntp": "НТП",
        "nck": "НЦК",
        "groups": f"группам ({', '.join(data.get('selected_head_names', []))})",
    }.get(recipients, "выбранным получателям")

    await progress_message.edit_text(
        f"""<b>✅ Рассылка завершена!</b>

<b>Получатели:</b> {recipient_type_text}
<b>Всего получателей:</b> {user_count}
<b>Успешно отправлено:</b> {success_count}
<b>Успешность:</b> {success_rate:.1f}%

<b>Сообщение было разослано!</b>""",
        reply_markup=broadcast_kb(),
    )

    logger.info(
        f"Рассылка завершена: {success_count}/{user_count} сообщений отправлено"
    )
    await state.clear()


@mip_broadcast_router.callback_query(BroadcastMenu.filter(F.action == "cancel"))
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    await state.clear()
    await callback.message.edit_text(
        """<b>📢 Рассылка</b>

Здесь ты можешь запустить рассылку сообщений по направлению

Отправь сообщение для рассылки:
• Текстовое сообщение  
• Сообщение с фото

<i>После отправки ты сможешь выбрать получателей</i>""",
        reply_markup=broadcast_kb(),
    )
    await state.set_state(BroadcastState.waiting_message)


@mip_broadcast_router.callback_query(BroadcastMenu.filter(F.action == "back"))
async def back_to_type_selection(callback: CallbackQuery, state: FSMContext):
    """Вернуться к выбору типа рассылки"""
    await show_broadcast_type_selection_callback(callback, state)


async def show_broadcast_type_selection_callback(
    callback: CallbackQuery, state: FSMContext
):
    """Показать выбор типа рассылки (для callback)"""
    data = await state.get_data()
    message_preview = data.get("message_text", "")
    if len(message_preview) > 100:
        message_preview = message_preview[:100] + "..."

    has_photo = data.get("message_type") == "photo"
    photo_text = "\n📸 С фото" if has_photo else ""

    await callback.message.edit_text(
        f"""<b>📢 Рассылка готова!</b>

<b>Сообщение:</b>
{message_preview}{photo_text}

<b>Выбери получателей:</b>""",
        reply_markup=broadcast_type_kb(),
    )

    await state.set_state(BroadcastState.selecting_type)
