import html
from datetime import datetime
from functools import wraps

from telegram.ext import CallbackContext

from IronRobo.modules.helper_funcs.misc import is_module_loaded

FILENAME = __name__.rsplit(".", 1)[-1]

# Log categories a group can switch on/off with /log and /nolog (like Rose).
CATEGORIES = {
    "settings": "Changes to group settings (locks, welcome, blacklist, flood, warn limit…)",
    "admin": "Admin actions (ban, mute, kick, warn, promote, pin, approve…)",
    "user": "Members joining and leaving",
    "automated": "Things I do on my own (antiflood, blacklist, warn filters)",
    "reports": "Reports with /report or @admin",
}

# Handlers whose logs belong to a category regardless of their tag.
FUNC_CATEGORY = {
    ("antiflood", "check_flood"): "automated",
    ("warns", "reply_filter"): "automated",
    ("reporting", "report"): "reports",
    ("welcome", "new_member"): "user",
}
# Log tags (the "#TAG" line) that are settings changes; everything else is admin.
SETTINGS_TAGS = {
    "LOCK",
    "UNLOCK",
    "Permission_LOCK",
    "SETFLOOD",
    "SET_WELCOME",
    "SET_GOODBYE",
    "RESET_WELCOME",
    "RESET_GOODBYE",
    "SET_WARN_LIMIT",
    "CLEAN_WELCOME",
    "WELCOME_MUTE",
    "BLACKLIST",
    "UNBLACKLIST",
    "AI_ENABLED",
    "AI_DISABLED",
}


def categorize(func, result):
    module = func.__module__.rsplit(".", 1)[-1]
    category = FUNC_CATEGORY.get((module, func.__name__))
    if category:
        return category
    for line in result.splitlines():
        line = line.strip()
        if line.startswith("#"):
            tag = line[1:].strip()
            return "settings" if tag in SETTINGS_TAGS else "admin"
    return "admin"


if is_module_loaded(FILENAME):
    from telegram import ParseMode, Update
    from telegram.error import BadRequest, TelegramError, Unauthorized
    from telegram.ext import CommandHandler, JobQueue, run_async
    from telegram.utils.helpers import escape_markdown

    from IronRobo import EVENT_LOGS, LOGGER, dispatcher
    from IronRobo.modules.helper_funcs.chat_status import user_admin
    from IronRobo.modules.sql import log_channel_sql as sql

    def _decorate(result, chat, message):
        datetime_fmt = "%H:%M - %d-%m-%Y"
        result += f"\n<b>Event Stamp</b>: <code>{datetime.utcnow().strftime(datetime_fmt)}</code>"
        if message and chat.type == chat.SUPERGROUP and chat.username:
            result += f'\n<b>Link:</b> <a href="https://t.me/{chat.username}/{message.message_id}">click here</a>'
        return result

    def send_chat_log(bot, chat, text, category="admin", message=None):
        """Send a log line to the group's log channel if that category is on."""
        log_chat = sql.get_chat_log_channel(chat.id)
        if not log_chat or category in sql.get_disabled_categories(chat.id):
            return
        _send(bot, log_chat, chat.id, _decorate(text, chat, message))

    def loggable(func):
        @wraps(func)
        def log_action(
            update: Update,
            context: CallbackContext,
            job_queue: JobQueue = None,
            *args,
            **kwargs,
        ):
            if not job_queue:
                result = func(update, context, *args, **kwargs)
            else:
                result = func(update, context, job_queue, *args, **kwargs)

            if result and isinstance(result, str):
                send_chat_log(
                    context.bot,
                    update.effective_chat,
                    result,
                    categorize(func, result),
                    update.effective_message,
                )
            return result

        return log_action

    def gloggable(func):
        @wraps(func)
        def glog_action(update: Update, context: CallbackContext, *args, **kwargs):
            result = func(update, context, *args, **kwargs)
            if result and isinstance(result, str) and EVENT_LOGS:
                chat = update.effective_chat
                _send(
                    context.bot,
                    str(EVENT_LOGS),
                    chat.id,
                    _decorate(result, chat, update.effective_message),
                )
            return result

        return glog_action

    def _send(bot, log_chat_id, orig_chat_id, result):
        try:
            bot.send_message(
                log_chat_id,
                result,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except BadRequest as excp:
            if excp.message == "Chat not found":
                bot.send_message(
                    orig_chat_id, "This log channel has been deleted - unsetting."
                )
                sql.stop_chat_logging(orig_chat_id)
            else:
                LOGGER.warning("Could not send log: %s", excp.message)
                try:
                    bot.send_message(
                        log_chat_id,
                        result
                        + "\n\nFormatting has been disabled due to an unexpected error.",
                    )
                except TelegramError:
                    pass
        except Unauthorized:
            LOGGER.warning("Can't post in the log channel of %s, unsetting it", orig_chat_id)
            sql.stop_chat_logging(orig_chat_id)
            try:
                bot.send_message(
                    orig_chat_id,
                    "I can't post in the log channel anymore (removed or not admin) - unsetting it.",
                )
            except TelegramError:
                pass
        except TelegramError as excp:
            LOGGER.warning("Could not send log: %s", excp)

    def _link_channel(bot, chat, channel_id, message):
        """Check the bot can post in the channel, then save it."""
        try:
            bot.send_message(
                channel_id,
                f"✅ This channel is now the log channel for {html.escape(chat.title or str(chat.id))}.",
                parse_mode=ParseMode.HTML,
            )
        except TelegramError as e:
            message.reply_text(
                "I can't post in that channel. Add me there as an admin "
                f"(with permission to post messages) and try again.\n\nError: {e.message}"
            )
            return False
        sql.set_chat_log_channel(chat.id, channel_id)
        return True

    @run_async
    @user_admin
    def logging(update: Update, context: CallbackContext):
        bot = context.bot
        message = update.effective_message
        chat = update.effective_chat

        log_channel = sql.get_chat_log_channel(chat.id)
        if log_channel:
            try:
                title = bot.get_chat(log_channel).title
            except TelegramError:
                title = "unknown"
            message.reply_text(
                f"This group has all it's logs sent to:"
                f" {escape_markdown(title)} (`{log_channel}`)",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            message.reply_text("No log channel has been set for this group!")

    @run_async
    @user_admin
    def setlog(update: Update, context: CallbackContext):
        bot = context.bot
        message = update.effective_message
        chat = update.effective_chat
        args = context.args

        if chat.type == chat.CHANNEL:
            message.reply_text(
                "Now, forward the /setlog to the group you want to tie this channel to!"
            )
            return
        if chat.type == chat.PRIVATE:
            message.reply_text("Send this in the group you want to log.")
            return

        if args:
            target = args[0]
            try:
                channel = bot.get_chat(int(target) if target.lstrip("-").isdigit() else target)
            except TelegramError:
                message.reply_text(
                    "I can't find that channel. Add me there as an admin first, then send "
                    "`/setlog <channel id or @username>` here.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            if channel.id == chat.id:
                message.reply_text("The log channel has to be a different chat.")
                return
            if _link_channel(bot, chat, channel.id, message):
                message.reply_text(
                    f"✅ Logs of this group will be sent to {channel.title}.\n"
                    "Use /logcategories to choose what gets logged."
                )
            return

        if message.forward_from_chat:
            channel_id = message.forward_from_chat.id
            try:
                message.delete()
            except BadRequest:
                pass
            if _link_channel(bot, chat, channel_id, message):
                bot.send_message(chat.id, "Successfully set log channel!")
            return

        message.reply_text(
            "To set a log channel:\n"
            " 1. Add me to the channel as an admin\n"
            " 2. Send `/setlog <channel id or @username>` here\n\n"
            "Or send /setlog in the channel and forward it here.",
            parse_mode=ParseMode.MARKDOWN,
        )

    @run_async
    @user_admin
    def unsetlog(update: Update, context: CallbackContext):
        bot = context.bot
        message = update.effective_message
        chat = update.effective_chat

        log_channel = sql.stop_chat_logging(chat.id)
        if log_channel:
            try:
                bot.send_message(log_channel, f"Channel has been unlinked from {chat.title}")
            except TelegramError:
                pass
            message.reply_text("Log channel has been un-set.")
        else:
            message.reply_text("No log channel has been set yet!")

    @run_async
    @user_admin
    def logcategories(update: Update, context: CallbackContext):
        chat = update.effective_chat
        disabled = sql.get_disabled_categories(chat.id)
        lines = [
            f"{'✅' if name not in disabled else '❌'} <code>{name}</code>: {html.escape(desc)}"
            for name, desc in CATEGORIES.items()
        ]
        text = "<b>Log categories</b>\n" + "\n".join(lines)
        text += "\n\nTurn one on/off with <code>/log &lt;category&gt;</code> and <code>/nolog &lt;category&gt;</code> (or <code>all</code>)."
        if not sql.get_chat_log_channel(chat.id):
            text += "\n\n⚠️ No log channel is set yet, see /setlog."
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)

    def _toggle(update: Update, context: CallbackContext, enable: bool):
        chat = update.effective_chat
        message = update.effective_message
        if not context.args:
            message.reply_text(
                f"Which one? Categories: {', '.join(CATEGORIES)} (or all)."
            )
            return
        wanted = {a.lower() for a in context.args}
        if "all" in wanted:
            wanted = set(CATEGORIES)
        unknown = wanted - set(CATEGORIES)
        if unknown:
            message.reply_text(
                f"Unknown category: {', '.join(sorted(unknown))}. "
                f"Categories: {', '.join(CATEGORIES)}."
            )
            return
        disabled = set(sql.get_disabled_categories(chat.id))
        disabled = disabled - wanted if enable else disabled | wanted
        sql.set_disabled_categories(chat.id, disabled)
        state = "on" if enable else "off"
        message.reply_text(f"Logging {state} for: {', '.join(sorted(wanted))}.")

    @run_async
    @user_admin
    def log_on(update: Update, context: CallbackContext):
        _toggle(update, context, True)

    @run_async
    @user_admin
    def log_off(update: Update, context: CallbackContext):
        _toggle(update, context, False)

    def __stats__():
        return f"• {sql.num_logchannels()} log channels set."

    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)

    def __chat_settings__(chat_id, user_id):
        log_channel = sql.get_chat_log_channel(chat_id)
        if log_channel:
            try:
                title = dispatcher.bot.get_chat(log_channel).title
            except TelegramError:
                title = "unknown"
            return f"This group has all it's logs sent to: {escape_markdown(title)} (`{log_channel}`)"
        return "No log channel is set for this group!"

    __help__ = """
I can log what happens in your group to a channel, like Rose.

*Admins only:*
 ❍ /setlog <channel id or @username>*:* Set the log channel (add me there as an admin first)
 ❍ /unsetlog*:* Stop logging
 ❍ /logchannel*:* Show the current log channel
 ❍ /logcategories*:* Show which kinds of events are logged
 ❍ /log <category>*:* Turn a category on (`all` for everything)
 ❍ /nolog <category>*:* Turn a category off

Categories: `settings`, `admin`, `user`, `automated`, `reports`.

You can also send /setlog inside the channel and forward that message to the group.
"""

    __mod_name__ = "Log Channel"

    LOG_HANDLER = CommandHandler("logchannel", logging)
    SET_LOG_HANDLER = CommandHandler("setlog", setlog)
    UNSET_LOG_HANDLER = CommandHandler("unsetlog", unsetlog)
    LOG_CATEGORIES_HANDLER = CommandHandler("logcategories", logcategories)
    LOG_ON_HANDLER = CommandHandler("log", log_on)
    LOG_OFF_HANDLER = CommandHandler("nolog", log_off)

    dispatcher.add_handler(LOG_HANDLER)
    dispatcher.add_handler(SET_LOG_HANDLER)
    dispatcher.add_handler(UNSET_LOG_HANDLER)
    dispatcher.add_handler(LOG_CATEGORIES_HANDLER)
    dispatcher.add_handler(LOG_ON_HANDLER)
    dispatcher.add_handler(LOG_OFF_HANDLER)

else:
    # run anyway if module not loaded
    def loggable(func):
        return func

    def gloggable(func):
        return func

    def send_chat_log(bot, chat, text, category="admin", message=None):
        return
