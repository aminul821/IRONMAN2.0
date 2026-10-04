import html
import io
import random
import traceback

from IronRobo import DEV_USERS, EVENT_LOGS, LOGGER, OWNER_ID, dispatcher
from telegram import Update
from telegram.error import NetworkError, RetryAfter, TimedOut, Unauthorized
from telegram.ext import CallbackContext, CommandHandler

# Errors that are part of normal operation and not worth reporting.
IGNORED_ERRORS = (NetworkError, TimedOut, RetryAfter, Unauthorized)


class ErrorsDict(dict):
    "A custom dict to store errors and their count"

    def __init__(self, *args, **kwargs):
        self.raw = []
        super().__init__(*args, **kwargs)

    def __contains__(self, error):
        self.raw.append(error)
        error.identifier = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
        for e in self:
            if type(e) is type(error) and e.args == error.args:
                self[e] += 1
                return True
        self[error] = 0
        return False

    def __len__(self):
        return len(self.raw)


errors = ErrorsDict()


def error_callback(update: object, context: CallbackContext):
    error = context.error
    if isinstance(error, IGNORED_ERRORS):
        LOGGER.warning("Telegram error while handling an update: %s", error)
        return
    LOGGER.error("Exception while handling an update", exc_info=error)
    if not isinstance(update, Update):
        return
    if error in errors:
        return

    tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    report = (
        "An exception was raised while handling an update\n"
        "User: {}\n"
        "Chat: {} {}\n"
        "Callback data: {}\n"
        "Message: {}\n\n"
        "Full Traceback: {}"
    ).format(
        update.effective_user.id if update.effective_user else "",
        update.effective_chat.title if update.effective_chat else "",
        update.effective_chat.id if update.effective_chat else "",
        update.callback_query.data if update.callback_query else "None",
        update.effective_message.text if update.effective_message else "No message",
        tb,
    )
    e = html.escape(f"{error}")
    doc = io.BytesIO(report.encode("utf-8"))
    doc.name = "error.txt"
    try:
        context.bot.send_document(
            EVENT_LOGS or OWNER_ID,
            doc,
            caption=f"#{error.identifier}\n<b>An unknown error occured:</b>\n<code>{e[:900]}</code>",
            parse_mode="html",
        )
    except Exception:
        LOGGER.exception("Could not send the error report")


def list_errors(update: Update, context: CallbackContext):
    if update.effective_user.id not in DEV_USERS:
        return
    e = {
        k: v for k, v in sorted(errors.items(), key=lambda item: item[1], reverse=True)
    }
    msg = "<b>Errors List:</b>\n"
    for x in e:
        msg += f"• <code>{html.escape(str(x))}:</code> <b>{e[x]}</b> #{x.identifier}\n"
    msg += f"{len(errors)} have occurred since startup."
    if len(msg) > 4096:
        doc = io.BytesIO(msg.encode("utf-8"))
        doc.name = "errors_msg.txt"
        context.bot.send_document(
            update.effective_chat.id,
            doc,
            caption="Too many errors have occured..",
        )
        return
    update.effective_message.reply_text(msg, parse_mode="html")


dispatcher.add_error_handler(error_callback)
dispatcher.add_handler(CommandHandler("errors", list_errors))
