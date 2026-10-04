import html

import requests
from IronRobo import dispatcher
from IronRobo.modules.disable import DisableAbleCommandHandler
from telegram import ParseMode, Update
from telegram.ext import CallbackContext


def ud(update: Update, context: CallbackContext):
    message = update.effective_message
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        message.reply_text("Give me a word to define, eg: /ud yeet")
        return
    text = parts[1]
    try:
        results = requests.get(
            "https://api.urbandictionary.com/v0/define",
            params={"term": text},
            timeout=15,
        ).json()
        first = results["list"][0]
        clean = lambda s: html.escape(s.replace("[", "").replace("]", ""))
        reply_text = (
            f"<b>{html.escape(text)}</b>\n\n{clean(first['definition'])}\n\n"
            f"<i>{clean(first.get('example', ''))}</i>"
        )
    except (requests.RequestException, ValueError):
        reply_text = "Urban Dictionary isn't reachable right now, try again later."
    except (KeyError, IndexError):
        reply_text = "No results found."
    message.reply_text(reply_text[:4096], parse_mode=ParseMode.HTML)


UD_HANDLER = DisableAbleCommandHandler(["ud"], ud, run_async=True)

dispatcher.add_handler(UD_HANDLER)

__command_list__ = ["ud"]
__handlers__ = [UD_HANDLER]
