from IronRobo import dispatcher
from IronRobo.modules.disable import DisableAbleCommandHandler
from IronRobo.utils.paste import paste_text
from telegram import Update
from telegram.ext import CallbackContext, run_async


@run_async
def paste(update: Update, context: CallbackContext):
    args = context.args
    message = update.effective_message

    if message.reply_to_message and (
        message.reply_to_message.text or message.reply_to_message.caption
    ):
        data = message.reply_to_message.text or message.reply_to_message.caption

    elif len(args) >= 1:
        data = message.text.split(None, 1)[1]

    else:
        message.reply_text("What am I supposed to do with this?")
        return

    url = paste_text(data)
    if not url:
        message.reply_text("Paste services are not reachable right now, try again later.")
        return

    message.reply_text(f"Pasted: {url}", disable_web_page_preview=True)


PASTE_HANDLER = DisableAbleCommandHandler("paste", paste)
dispatcher.add_handler(PASTE_HANDLER)

__help__ = """
 • `/paste`*:* Reply to a message (or give text) to upload it to a paste service
"""
__mod_name__ = "Paste"
__command_list__ = ["paste"]
__handlers__ = [PASTE_HANDLER]
