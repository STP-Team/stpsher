import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.handlers.user.main import user_start_cmd
from tgbot.misc.helpers import generate_auth_code
from tgbot.misc.states.user.auth import Authorization
from tgbot.services.mailing import send_auth_email

user_auth_router = Router()
user_auth_router.message.filter(F.chat.type == "private")
user_auth_router.callback_query.filter(F.message.chat.type == "private")


@user_auth_router.callback_query(F.data == "auth")
async def user_auth(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    bot_message = await callback.message.edit_text("""<b>🔑 Авторизация</b>

Отлично, теперь введи свою рабочую почту

<i>Можешь найти ее на mail.domru.ru нажав на аватарку в правом верхнем углу</i>""")
    await state.set_state(Authorization.email)
    await state.update_data(bot_message_id=bot_message.message_id)


@user_auth_router.message(Authorization.email)
async def user_auth_email(message: Message, state: FSMContext):
    email_pattern = r"^[A-Za-z0-9._%+-]+@dom\.ru$"
    state_data = await state.get_data()
    await message.delete()

    if not re.match(email_pattern, message.text):
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=state_data.get("bot_message_id"),
            text=f"""<b>🔑 Авторизация</b>

Рабочая почта должна содержать <code>@dom.ru</code>
Ты ввел <code>{message.text}</code>

Попробуй еще раз 🙏

<i>Можешь найти почту на mail.domru.ru нажав на аватарку в правом верхнем углу</i>""",
        )
        return

    auth_code = generate_auth_code()
    bot_info = await message.bot.get_me()
    await state.update_data(email=message.text, auth_code=auth_code)
    await state.set_state(Authorization.auth_code)
    await send_auth_email(
        code=auth_code, email=message.text, bot_username=bot_info.username
    )

    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=state_data.get("bot_message_id"),
        text=f"""<b>🔐 Код с почты</b>

Отправил на почту <code>{message.text}</code> код подтверждения

Напиши полученный код в чат для завершения авторизации

<i>Если письмо не пришло - проверь папку СПАМ
Письмо поступит от отправителя <code>shedule-botntp2@mail.ru</code></i>""",
    )


@user_auth_router.message(Authorization.auth_code)
async def user_auth_code(message: Message, state: FSMContext):
    state_data = await state.get_data()

    await message.delete()
    if not message.text == state_data.get("auth_code"):
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=state_data.get("bot_message_id"),
            text=f"""<b>🔐 Код с почты</b>

Ты ввел неверный код :(
Введи код с рабочей почты <code>{state_data.get("email")}</code>

<i>Если письмо не пришло - проверь папку СПАМ
Письмо поступит от отправителя <code>shedule-botntp2@mail.ru</code></i>""",
        )
        return

    await state.set_state(Authorization.fullname)
    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=state_data.get("bot_message_id"),
        text="""<b>✍ Проверка ФИО</b>

Супер, код верный. И последнее, напиши свои ФИО 

<i>Например: Иванов Иван Иванович</i>""",
    )


@user_auth_router.message(Authorization.fullname)
async def user_auth_fullname(
    message: Message, state: FSMContext, stp_repo: MainRequestsRepo
):
    fullname_pattern = r"^[А-Яа-яЁё]+ [А-Яа-яЁё]+ [А-Яа-яЁё]+$"
    state_data = await state.get_data()
    await message.delete()

    if not re.match(fullname_pattern, message.text):
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=state_data.get("bot_message_id"),
            text="""<b>✍ Проверка ФИО</b>

Формат ФИО неверный :(
Попробуй еще раз

<i>Например: Иванов Иван Иванович</i>""",
        )
        return

    db_user: Employee | None = await stp_repo.employee.get_user(fullname=message.text)
    if db_user:
        if not db_user.user_id:
            db_user.user_id = message.chat.id
            if message.from_user.username:
                db_user.username = message.from_user.username
            db_user.email = state_data.get("email")
            db_user.role = 1
            await stp_repo.session.commit()

            await state.clear()
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=state_data.get("bot_message_id"),
                text="""<b>✅ Успешная авторизация</b>

Супер, авторизация пройдена. Теперь у тебя есть доступ ко всем ботам СТП 🥳""",
            )
            await user_start_cmd(message=message, user=db_user, stp_repo=stp_repo)
            return
        else:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=state_data.get("bot_message_id"),
                text="""<b>✍ Проверка ФИО</b>

Пользователем с такими ФИО уже зарегистрирован, попробуй еще раз

<i>Если ты считаешь, что произошла ошибка - напиши письмо на рассылку <code>СТП_РАССЫЛКА_МИП</code> с описанием ситуации</i>""",
            )
            return
    else:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=state_data.get("bot_message_id"),
            text="""<b>✍ Проверка ФИО</b>

Пользователем с такими ФИО не найден в базе, попробуй еще раз

<i>Если ты считаешь, что произошла ошибка - напиши письмо на рассылку <code>СТП_РАССЫЛКА_МИП</code> с описанием ситуации</i>""",
        )
        return
