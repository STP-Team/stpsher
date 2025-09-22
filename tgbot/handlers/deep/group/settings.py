from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import ChatMember, Message
from aiogram.utils.payload import decode_payload

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.deep import DeepLinkRegexFilter

deeplink_group = Router()


@deeplink_group.message(
    CommandStart(deep_link=True), DeepLinkRegexFilter(r"^group_-?\d+$")
)
async def handle_settings(
    message: Message, command: CommandObject, stp_repo: MainRequestsRepo
):
    payload = decode_payload(command.args)
    group_id = payload.split("_", 1)[1]

    member: ChatMember = await message.bot.get_chat_member(
        chat_id=group_id, user_id=message.from_user.id
    )

    if member.status in ["administrator", "creator"]:
        group = await stp_repo.group.get_group(int(group_id))
        await message.answer(f"""⚙️ <b>Настройки группы</b>
    
<b>Проверка регистрации:</b> {"🟢 Активна" if group.remove_unemployed else "🟠 Выключена"}
<b>Уведомление о новеньких:</b> {"🟢 Активно" if group.new_user_notify else "🟠 Выключено"}
    
<b>Казино:</b> {"🟢 Разрешено" if group.is_casino_allowed else "🟠 Запрещено"}""")
    else:
        await message.answer("ты не админ")
