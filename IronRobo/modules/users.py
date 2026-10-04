import time
import threading
from io import BytesIO
from time import sleep

from telegram import TelegramError, Update
from telegram.error import BadRequest, Unauthorized
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    run_async,
)

import IronRobo.modules.sql.users_sql as sql
from IronRobo import DEV_USERS, LOGGER, OWNER_ID, dispatcher
from IronRobo.modules.helper_funcs.chat_status import dev_plus, sudo_plus
from IronRobo.modules.sql.users_sql import get_all_users

USERS_GROUP = 4
CHAT_GROUP = 5
DEV_AND_MORE = DEV_USERS.append(int(OWNER_ID))


def get_user_id(username):
    # ensure valid userid
    if len(username) <= 5:
        return None

    if username.startswith("@"):
        username = username[1:]

    users = sql.get_userid_by_name(username)

    if not users:
        return None

    elif len(users) == 1:
        return users[0].user_id

    else:
        for user_obj in users:
            try:
                userdat = dispatcher.bot.get_chat(user_obj.user_id)
                if userdat.username == username:
                    return userdat.id

            except BadRequest as excp:
                if excp.message == "Chat not found":
                    pass
                else:
                    LOGGER.exception("Error extracting user ID")

    return None


@run_async
@dev_plus
def broadcast(update: Update, context: CallbackContext):
    to_send = update.effective_message.text.split(None, 1)

    if len(to_send) >= 2:
        to_group = False
        to_user = False
        if to_send[0] == "/broadcastgroups":
            to_group = True
        if to_send[0] == "/broadcastusers":
            to_user = True
        else:
            to_group = to_user = True
        chats = sql.get_all_chats() or []
        users = get_all_users()
        failed = 0
        failed_user = 0
        if to_group:
            for chat in chats:
                try:
                    context.bot.sendMessage(
                        int(chat.chat_id),
                        to_send[1],
                        parse_mode="MARKDOWN",
                        disable_web_page_preview=True,
                    )
                    sleep(0.1)
                except TelegramError:
                    failed += 1
        if to_user:
            for user in users:
                try:
                    context.bot.sendMessage(
                        int(user.user_id),
                        to_send[1],
                        parse_mode="MARKDOWN",
                        disable_web_page_preview=True,
                    )
                    sleep(0.1)
                except TelegramError:
                    failed_user += 1
        update.effective_message.reply_text(
            f"Broadcast complete.\nGroups failed: {failed}.\nUsers failed: {failed_user}."
        )


# update_user costs several database round trips, so only write when
# something changed or the entry is older than SEEN_TTL seconds.
SEEN_TTL = 6 * 60 * 60
SEEN_MAX = 50000
_seen = {}
_seen_lock = threading.Lock()
CHAT_CHECK_INTERVAL = 10 * 60
_chat_checked = {}


def _remember(user_id, username, chat_id=None, chat_title=None):
    """True if this user/chat combination still needs to be written."""
    key = (user_id, chat_id)
    value = (username, chat_title)
    now = time.monotonic()
    with _seen_lock:
        old = _seen.get(key)
        if old and old[0] == value and now - old[1] < SEEN_TTL:
            return False
        if len(_seen) >= SEEN_MAX:
            _seen.clear()
        _seen[key] = (value, now)
    return True


def _update_user(user_id, username, chat_id=None, chat_title=None):
    if _remember(user_id, username, chat_id, chat_title):
        try:
            sql.update_user(user_id, username, chat_id, chat_title)
        except Exception:
            with _seen_lock:
                _seen.pop((user_id, chat_id), None)
            raise


@run_async
def log_user(update: Update, context: CallbackContext):
    chat = update.effective_chat
    msg = update.effective_message
    if not msg.from_user:
        return

    _update_user(msg.from_user.id, msg.from_user.username, chat.id, chat.title)

    if msg.reply_to_message and msg.reply_to_message.from_user:
        _update_user(
            msg.reply_to_message.from_user.id,
            msg.reply_to_message.from_user.username,
            chat.id,
            chat.title,
        )

    if msg.forward_from:
        _update_user(msg.forward_from.id, msg.forward_from.username)


@run_async
@sudo_plus
def chats(update: Update, context: CallbackContext):
    all_chats = sql.get_all_chats() or []
    chatfile = "List of chats.\n0. Chat name | Chat ID | Members count\n"
    P = 1
    for chat in all_chats:
        try:
            curr_chat = context.bot.getChat(chat.chat_id)
            bot_member = curr_chat.get_member(context.bot.id)
            chat_members = curr_chat.get_member_count()
            chatfile += "{}. {} | {} | {}\n".format(
                P, chat.chat_name, chat.chat_id, chat_members
            )
            P = P + 1
        except:
            pass

    with BytesIO(str.encode(chatfile)) as output:
        output.name = "groups_list.txt"
        update.effective_message.reply_document(
            document=output,
            filename="groups_list.txt",
            caption="Here be the list of groups in my database.",
        )


@run_async
def chat_checker(update: Update, context: CallbackContext):
    bot = context.bot
    chat_id = update.effective_message.chat.id
    now = time.monotonic()
    # one Telegram API call per chat every CHAT_CHECK_INTERVAL, not per message
    with _seen_lock:
        if now - _chat_checked.get(chat_id, -CHAT_CHECK_INTERVAL) < CHAT_CHECK_INTERVAL:
            return
        _chat_checked[chat_id] = now
    try:
        if update.effective_message.chat.get_member(bot.id).can_send_messages is False:
            bot.leaveChat(chat_id)
    except Unauthorized:
        pass


def __user_info__(user_id):
    if user_id in [777000, 1087968824]:
        return """╘══「 Groups count: <code>???</code> 」"""
    if user_id == dispatcher.bot.id:
        return """╘══「 Groups count: <code>???</code> 」"""
    num_chats = sql.get_user_num_chats(user_id)
    return f"""╘══「 Groups count: <code>{num_chats}</code> 」"""


def __stats__():
    return f"• {sql.num_users()} users, across {sql.num_chats()} chats"


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


__help__ = ""  # no help string

BROADCAST_HANDLER = CommandHandler(
    ["broadcastall", "broadcastusers", "broadcastgroups"], broadcast
)
USER_HANDLER = MessageHandler(Filters.all & Filters.group, log_user)
CHAT_CHECKER_HANDLER = MessageHandler(Filters.all & Filters.group, chat_checker)
CHATLIST_HANDLER = CommandHandler("groups", chats)

dispatcher.add_handler(USER_HANDLER, USERS_GROUP)
dispatcher.add_handler(BROADCAST_HANDLER)
dispatcher.add_handler(CHATLIST_HANDLER)
dispatcher.add_handler(CHAT_CHECKER_HANDLER, CHAT_GROUP)

__mod_name__ = "Users"
__handlers__ = [(USER_HANDLER, USERS_GROUP), BROADCAST_HANDLER, CHATLIST_HANDLER]
