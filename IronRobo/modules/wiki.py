import html
import io
from urllib.parse import quote

import wikipedia
from IronRobo import dispatcher
from IronRobo.modules.disable import DisableAbleCommandHandler
from telegram import ParseMode, Update
from telegram.ext import CallbackContext
from wikipedia.exceptions import DisambiguationError, PageError


def wiki(update: Update, context: CallbackContext):
    message = update.effective_message
    parts = message.text.split(" ", maxsplit=1)
    if len(parts) > 1:
        search = parts[1]
    elif message.reply_to_message and message.reply_to_message.text:
        search = message.reply_to_message.text
    else:
        message.reply_text("Give me something to search, eg: `/wiki Python`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        page = wikipedia.page(search, auto_suggest=False)
        res = page.summary
        title, url = page.title, page.url
    except DisambiguationError as e:
        options = "\n".join(html.escape(o) for o in e.options[:10])
        message.reply_text(
            f"Disambiguated pages found! Adjust your query accordingly.\n<i>{options}</i>",
            parse_mode=ParseMode.HTML,
        )
        return
    except PageError:
        try:
            res = wikipedia.summary(search)
            title, url = search, f"https://en.wikipedia.org/wiki/{quote(search.replace(' ', '_'))}"
        except Exception:
            message.reply_text("No results found.")
            return
    except Exception:
        message.reply_text("Wikipedia isn't reachable right now, try again later.")
        return

    result = f"<b>{html.escape(title)}</b>\n\n<i>{html.escape(res)}</i>\n"
    result += f'<a href="{html.escape(url)}">Read more...</a>'
    if len(result) > 4000:
        doc = io.BytesIO(f"{title}\n\n{res}\n\n{url}".encode("utf-8"))
        doc.name = "result.txt"
        context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=doc,
            reply_to_message_id=message.message_id,
            caption=title[:1000],
        )
    else:
        message.reply_text(result, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


WIKI_HANDLER = DisableAbleCommandHandler("wiki", wiki, run_async=True)
dispatcher.add_handler(WIKI_HANDLER)
