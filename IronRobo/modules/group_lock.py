"""Keep the bot to its own groups.

With ALLOWED_GROUPS set, the bot only works in those groups and in groups the
owner (or a dev user) adds it to; those are remembered. If anyone else adds
it somewhere, or it is still in some other group, it leaves. BL_CHATS are
always left. Without ALLOWED_GROUPS the bot works everywhere (except BL_CHATS).
"""
import threading
import time

from IronRobo import ALLOWED_GROUPS, BL_CHATS, DEV_USERS, LOGGER, OWNER_ID, dispatcher
from IronRobo.modules.helper_funcs.filters import CustomFilters
from IronRobo.modules.sql_extended import allowed_chats_sql as sql
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext, CommandHandler, DispatcherHandlerStop, TypeHandler

LOCK_ENABLED = bool(ALLOWED_GROUPS)
GUARD_GROUP = -100  # runs before every other handler
LEAVE_RETRY = 60  # seconds before trying to leave the same chat again
_leaving = {}
_leaving_lock = threading.Lock()


def chat_allowed(chat_id) -> bool:
    if chat_id in BL_CHATS:
        return False
    if not LOCK_ENABLED:
        return True
    return chat_id in ALLOWED_GROUPS or sql.is_allowed(chat_id)


def _leave(bot, chat_id, text=None):
    now = time.monotonic()
    with _leaving_lock:
        if now - _leaving.get(chat_id, -LEAVE_RETRY) < LEAVE_RETRY:
            return
        _leaving[chat_id] = now
    try:
        if text:
            bot.send_message(chat_id, text)
    except TelegramError:
        pass
    try:
        bot.leave_chat(chat_id)
        LOGGER.info("Left chat %s (not an allowed group)", chat_id)
    except TelegramError as e:
        LOGGER.warning("Could not leave chat %s: %s", chat_id, e)


def guard(update: Update, context: CallbackContext):
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    if chat_allowed(chat.id):
        return

    bot = context.bot
    msg = update.effective_message
    if not msg:
        # Member-status updates: the "added to group" message decides, not these.
        member_update = update.my_chat_member
        if (
            member_update
            and member_update.new_chat_member.status in ("member", "administrator")
            and (member_update.from_user.id == OWNER_ID or member_update.from_user.id in DEV_USERS)
            and chat.id not in BL_CHATS
        ):
            sql.allow(chat.id)
            LOGGER.info("Owner added me to %s (%s), allowing it", chat.title, chat.id)
            return
        raise DispatcherHandlerStop
    added_me = bool(
        msg
        and msg.new_chat_members
        and any(member.id == bot.id for member in msg.new_chat_members)
    )
    adder = msg.from_user if msg else None
    if (
        added_me
        and adder
        and (adder.id == OWNER_ID or adder.id in DEV_USERS)
        and chat.id not in BL_CHATS
    ):
        sql.allow(chat.id)
        LOGGER.info("Owner added me to %s (%s), allowing it", chat.title, chat.id)
        return  # let the normal welcome run

    _leave(
        bot,
        chat.id,
        "🦾 Sorry, ye Iron Man private hai. Sirf owner ke groups mein kaam karta hoon. Bye! 👋"
        if added_me
        else None,
    )
    raise DispatcherHandlerStop


def _target_chat(update: Update, context: CallbackContext):
    if context.args:
        try:
            return int(context.args[0])
        except ValueError:
            return None
    chat = update.effective_chat
    return chat.id if chat.type != "private" else None


def allowgroup(update: Update, context: CallbackContext):
    msg = update.effective_message
    chat_id = _target_chat(update, context)
    if chat_id is None:
        msg.reply_text("Usage: /allowgroup <chat id> (or send it in the group)")
        return
    sql.allow(chat_id)
    msg.reply_text(f"✅ Group {chat_id} is allowed now.")


def disallowgroup(update: Update, context: CallbackContext):
    msg = update.effective_message
    chat_id = _target_chat(update, context)
    if chat_id is None:
        msg.reply_text("Usage: /disallowgroup <chat id> (or send it in the group)")
        return
    if chat_id in ALLOWED_GROUPS:
        msg.reply_text("That group is in ALLOWED_GROUPS; remove it from the settings instead.")
        return
    sql.disallow(chat_id)
    msg.reply_text(f"❌ Group {chat_id} is no longer allowed, leaving it.")
    if LOCK_ENABLED:
        _leave(context.bot, chat_id)


def allowedgroups(update: Update, context: CallbackContext):
    if not LOCK_ENABLED:
        update.effective_message.reply_text(
            "Group lock is off (ALLOWED_GROUPS isn't set), I work in every group."
        )
        return
    lines = [f"• {cid} (settings)" for cid in sorted(ALLOWED_GROUPS)]
    lines += [f"• {cid} (added by owner)" for cid in sql.all_allowed() if int(cid) not in ALLOWED_GROUPS]
    update.effective_message.reply_text("Allowed groups:\n" + "\n".join(lines))


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


owner_filter = CustomFilters.dev_filter
dispatcher.add_handler(TypeHandler(Update, guard), GUARD_GROUP)
dispatcher.add_handler(CommandHandler("allowgroup", allowgroup, filters=owner_filter, run_async=True))
dispatcher.add_handler(CommandHandler("disallowgroup", disallowgroup, filters=owner_filter, run_async=True))
dispatcher.add_handler(CommandHandler("allowedgroups", allowedgroups, filters=owner_filter, run_async=True))

__mod_name__ = "Group Lock"
__help__ = """
*Owner only.* With `ALLOWED_GROUPS` set I only work in those groups and in groups the owner adds me to; anywhere else I leave.

 • `/allowgroup <chat id>`*:* Allow a group (or send it inside the group)
 • `/disallowgroup <chat id>`*:* Remove a group and leave it
 • `/allowedgroups`*:* List the allowed groups
"""
