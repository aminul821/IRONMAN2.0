import html

from gpytranslate import Translator
from IronRobo import pbot
from pyrogram import filters
from pyrogram.types import Message

trans = Translator()


@pbot.on_message(filters.command(["tr", "tl"]))
async def translate(_, message: Message) -> None:
    reply_msg = message.reply_to_message
    if not reply_msg:
        await message.reply_text("Reply to a message to translate it!")
        return
    to_translate = reply_msg.caption or reply_msg.text
    if not to_translate:
        await message.reply_text("That message has no text to translate!")
        return
    try:
        args = message.text.split()[1].lower()
        if "//" in args:
            source, dest = args.split("//", 1)
        else:
            source = await trans.detect(to_translate)
            dest = args
    except IndexError:
        source = await trans.detect(to_translate)
        dest = "en"
    try:
        translation = await trans(to_translate, sourcelang=source, targetlang=dest)
    except Exception as e:
        await message.reply_text(f"Translation failed: {html.escape(str(e))}", parse_mode="html")
        return
    reply = (
        f"<b>Translated from {html.escape(source)} to {html.escape(dest)}</b>:\n"
        f"<code>{html.escape(translation.text)}</code>"
    )

    await message.reply_text(reply, parse_mode="html")


__help__ = """ 
Use this module to translate stuff!
*Commands:*
   ➢ `/tl` (or `/tr`): as a reply to a message, translates it to English.
   ➢ `/tl <lang>`: translates to <lang>
eg: `/tl ja`: translates to Japanese.
   ➢ `/tl <source>//<dest>`: translates from <source> to <lang>.
eg: `/tl ja//en`: translates from Japanese to English.
• [List of supported languages for translation](https://telegra.ph/Lang-Codes-03-19-3)
"""

__mod_name__ = "Translator"
__command_list__ = ["tr", "tl"]
