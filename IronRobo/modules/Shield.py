import asyncio
import os
import re

from better_profanity import profanity
from telethon import events

from IronRobo import BOT_ID, LOGGER
from IronRobo import telethn as tbot
from IronRobo.events import register
from IronRobo.modules.sql_extended import shield_sql
from IronRobo.utils.translate import detect
from IronRobo.modules.sql_extended.nsfw_watch_sql import (
    add_nsfwatch,
    is_nsfwatch_indb,
    rmnsfwatch,
)

# The NSFW media watcher itself lives in the "NSFW Watch" module; /gshield just
# toggles the same setting.

_WORDLIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "profanity_wordlist.txt",
)
if os.path.exists(_WORDLIST):
    profanity.load_censor_words_from_file(_WORDLIST)
else:
    profanity.load_censor_words()

ON = ("on", "yes", "enable")
OFF = ("off", "no", "disable")


async def is_admin(event, user_id):
    try:
        perms = await event.client.get_permissions(event.chat_id, user_id)
    except Exception:
        return False
    return perms.is_admin or perms.is_creator


async def _check_rights(event):
    if not event.is_group:
        await event.reply("This command only works in groups.")
        return False
    if not await is_admin(event, BOT_ID):
        await event.reply("`I Should Be Admin To Do This!`")
        return False
    if not await is_admin(event, event.sender_id):
        await event.reply("`You Should Be Admin To Do This!`")
        return False
    return True


@register(pattern="^/gshield(?: |$)(.*)")
async def gshield(event):
    if not await _check_rights(event):
        return
    input_str = event.pattern_match.group(1).strip().lower()
    if input_str in ON:
        if is_nsfwatch_indb(str(event.chat_id)):
            await event.reply("`This Chat Has Already Enabled Nsfw Watch.`")
            return
        add_nsfwatch(str(event.chat_id))
        await event.reply(
            f"**Added Chat {event.chat.title} With Id {event.chat_id} To Database. This Groups Nsfw Contents Will Be Deleted**"
        )
    elif input_str in OFF:
        if not is_nsfwatch_indb(str(event.chat_id)):
            await event.reply("This Chat Has Not Enabled Nsfw Watch.")
            return
        rmnsfwatch(str(event.chat_id))
        await event.reply(
            f"**Removed Chat {event.chat.title} With Id {event.chat_id} From Nsfw Watch**"
        )
    else:
        state = "on" if is_nsfwatch_indb(str(event.chat_id)) else "off"
        await event.reply(
            f"I understand `/gshield on` and `/gshield off` only.\n\nCurrent setting is : **{state}**"
        )


async def _toggle(event, name, is_on, set_on):
    if not await _check_rights(event):
        return
    input_str = event.pattern_match.group(1).strip().lower()
    if input_str in ON:
        if is_on(event.chat_id):
            await event.reply(f"{name} is already activated for this chat.")
            return
        set_on(event.chat_id, True)
        await event.reply(f"{name} turned on for this chat.")
    elif input_str in OFF:
        if not is_on(event.chat_id):
            await event.reply(f"{name} isn't turned on for this chat.")
            return
        set_on(event.chat_id, False)
        await event.reply(f"{name} turned off for this chat.")
    else:
        state = "on" if is_on(event.chat_id) else "off"
        await event.reply(
            f"Please provide some input: on or off.\n\nCurrent setting is : **{state}**"
        )


@register(pattern="^/profanity(?: |$)(.*)")
async def profanity_cmd(event):
    await _toggle(
        event, "Profanity filter", shield_sql.is_profanity, shield_sql.set_profanity
    )


@register(pattern="^/globalmode(?: |$)(.*)")
async def globalmode_cmd(event):
    await _toggle(
        event, "English only mode", shield_sql.is_english_only, shield_sql.set_english_only
    )


MARKDOWN_LINK = re.compile(r"\[([^]]+)]\(\s*([^)]+)\s*\)")


def _clean_text(msg):
    """Drop mentions, hashtags, commands and links before detecting the language."""
    msg = MARKDOWN_LINK.sub("", msg)
    words = [w for w in msg.split() if w[0] not in "@#/" and not w.startswith("http")]
    return " ".join(words)


async def _warn(event, text):
    try:
        await event.delete()
    except Exception:
        return
    dev = await event.respond(text)
    await asyncio.sleep(10)
    try:
        await dev.delete()
    except Exception:
        pass


@tbot.on(events.NewMessage(incoming=True))
async def shield_watcher(event):
    if event.is_private or not event.text:
        return
    profanity_on = shield_sql.is_profanity(event.chat_id)
    english_on = shield_sql.is_english_only(event.chat_id)
    if not (profanity_on or english_on):
        return
    if await is_admin(event, event.sender_id):
        return
    sender = await event.get_sender()
    name = getattr(sender, "first_name", None) or "User"
    mention = f"[{name}](tg://user?id={event.sender_id})"

    if profanity_on and profanity.contains_profanity(event.text):
        await _warn(
            event,
            f"{mention}, your message contained a slang word and has been deleted.",
        )
        return

    if english_on:
        text = _clean_text(event.text)
        if len(text) < 4 or not any(c.isalpha() for c in text):
            return
        try:
            lang = await detect(text)
        except Exception as e:
            LOGGER.debug("Language detection failed: %s", e)
            return
        if lang and lang != "en":
            await _warn(event, f"{mention} you should only speak in english here !")


__help__ = """
<b> Group Guardian: </b>
✪ Ironman can protect your group from NSFW senders, Slag word users and also can force members to use English

<b>Commmands</b>
 - /gshield <i>on/off</i> - Enable|Disable Porn cleaning
 - /globalmode <i>on/off</i> - Enable|Disable English only mode
 - /profanity <i>on/off</i> - Enable|Disable slag word cleaning
"""
__mod_name__ = "Shield"
