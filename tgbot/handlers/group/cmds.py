import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from tgbot.keyboards.group.cmds import GroupsCmdsMenu, groups_cmds_kb
from tgbot.keyboards.group.main import GroupsMenu

logger = logging.getLogger(__name__)

group_cmds_router = Router()
group_cmds_router.message.filter(F.chat.type == "private")
group_cmds_router.callback_query.filter(F.message.chat.type == "private")


@group_cmds_router.callback_query(GroupsMenu.filter(F.menu == "cmds"))
async def group_cmds_cb(callback: CallbackQuery):
    await callback.message.edit_text(
        """👯‍♀️ <b>Группы - Команды</b>

Выбери категорию команд, которую хочешь изучить:

<blockquote expandable><b>🛡️ Команды для администраторов</b>
∙ Управление пользователями (мут, бан)
∙ Управление сообщениями (закрепление)
∙ Настройки группы</blockquote>

<blockquote expandable><b>🙋🏻‍♂️ Команды для пользователей</b>
∙ Информация о группе
∙ Игры казино
∙ Просмотр рейтинга и баланса</blockquote>""",
        reply_markup=groups_cmds_kb(),
    )


@group_cmds_router.callback_query(GroupsCmdsMenu.filter(F.menu == "admins"))
async def admin_commands_cb(callback: CallbackQuery):
    await callback.message.edit_text(
        """🛡️ <b>Команды для администраторов групп</b>

<b>📌 Управление сообщениями:</b>
∙ <code>/pin</code> - закрепить сообщение (в ответ на сообщение)
∙ <code>/unpin</code> - открепить сообщение (в ответ на закрепленное сообщение)

<b>👥 Управление пользователями:</b>
∙ <code>/mute [время]</code> - замутить пользователя (в ответ на сообщение или /mute user_id)
∙ <code>/unmute</code> - размутить пользователя (в ответ на сообщение или /unmute user_id)
∙ <code>/ban</code> - забанить пользователя (в ответ на сообщение или /ban user_id)
∙ <code>/unban</code> - разбанить пользователя (в ответ на сообщение или /unban user_id)

<b>⚙️ Настройки группы:</b>
∙ <code>/settings</code> - настройки группы

<b>📝 Примеры времени для мута:</b>
∙ <code>/mute 30m</code> или <code>/mute 30м</code> - на 30 минут
∙ <code>/mute 2h</code> или <code>/mute 2ч</code> - на 2 часа
∙ <code>/mute 7d</code> или <code>/mute 7д</code> - на 7 дней
∙ <code>/mute</code> - навсегда""",
        reply_markup=groups_cmds_kb(),
    )


@group_cmds_router.callback_query(GroupsCmdsMenu.filter(F.menu == "users"))
async def user_commands_cb(callback: CallbackQuery):
    await callback.message.edit_text(
        """🙋🏻‍♂️ <b>Команды для пользователей в группах</b>

<b>ℹ️ Информация о группе:</b>
∙ <code>/admins</code> - список администраторов группы

<b>💰 Баланс и рейтинг:</b>
∙ <code>/balance</code> - посмотреть свой баланс баллов
∙ <code>/top</code> - рейтинг участников группы по баллам

<b>🎰 Игры казино:</b>
∙ <code>/slots [сумма]</code> - игра в слоты (пример: /slots 50)
∙ <code>/dice [сумма]</code> - игра в кости (пример: /dice 100)
∙ <code>/darts [сумма]</code> - игра в дартс (пример: /darts 25)
∙ <code>/bowling [сумма]</code> - игра в боулинг (пример: /bowling 75)

<b>💡 Примечания:</b>
∙ Минимальная ставка для игр - 10 баллов
∙ Команды /balance и казино доступны только специалистам и дежурным
∙ Казино может быть отключено администратором группы""",
        reply_markup=groups_cmds_kb(),
    )
