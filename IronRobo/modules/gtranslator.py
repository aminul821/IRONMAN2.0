import html

from IronRobo import pbot
from IronRobo.utils.translate import TranslateUnavailable, translate
from pyrogram import filters
from pyrogram.types import Message

@pbot.on_message(filters.command(["tr", "tl"]))
async def translate_cmd(_, message: Message) -> None:
    reply_msg = message.reply_to_message
    if not reply_msg:
        await message.reply_text("Reply to a message to translate it!")
        return
    to_translate = reply_msg.caption or reply_msg.text
    if not to_translate:
        await message.reply_text("That message has no text to translate!")
        return
    args = message.text.split()
    source, dest = "auto", "en"
    if len(args) > 1:
        lang = args[1].lower()
        if "//" in lang:
            source, dest = lang.split("//", 1)
        else:
            dest = lang
    try:
        translation = await translate(to_translate, source=source, dest=dest)
    except TranslateUnavailable:
        await message.reply_text("Google Translate is busy right now, try again in a minute.")
        return
    if source == "auto":
        source = translation.lang or "auto"
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
