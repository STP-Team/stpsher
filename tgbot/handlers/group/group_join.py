from aiogram import Router
from aiogram.filters import IS_ADMIN, IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated

chat_member = Router()


@chat_member.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_MEMBER)
)
async def bot_added_to_group(event: ChatMemberUpdated):
    """Handle when bot is added to a group."""
    if event.chat.type in ["group", "supergroup"]:
        await event.answer("""<b>Привет 👋</b>

Для корректной работы мне необходимо выдать права администратора

Для выдачи прав:
1. Открой настройки группы
2. Найди бота в списке участников
3. Выдай стандартные права администратора""")


@chat_member.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER >> IS_ADMIN)
)
async def bot_got_admin_rights(event: ChatMemberUpdated):
    """Handle when bot gets admin rights in a group."""
    if event.chat.type in ["group", "supergroup"]:
        await event.answer("""<b>Спасибо 🙏🏻</b>

Права администратора успешно выданы, и бот готов к работе

Для проверки и изменения настроек группы используй команду /settings""")


@chat_member.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_ADMIN >> IS_MEMBER)
)
async def bot_lost_admin_rights(event: ChatMemberUpdated):
    """Handle when bot gets admin rights in a group."""
    if event.chat.type in ["group", "supergroup"]:
        await event.answer("""<b>Права администратора удалены 🥹</b>

Без наличия прав я не смогу корректно работать в группе""")
