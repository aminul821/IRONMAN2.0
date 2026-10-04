import asyncio
import os
import tempfile

from gtts import gTTS, gTTSError
from IronRobo import telethn as tbot
from IronRobo.events import register


async def is_register_admin(event, user_id):
    try:
        perms = await event.client.get_permissions(event.chat_id, user_id)
    except Exception:
        return False
    return perms.is_admin or perms.is_creator


@register(pattern="^/tts ?(.*)")
async def tts(event):
    if event.fwd_from:
        return
    if event.is_group and not await is_register_admin(event, event.sender_id):
        await event.reply("🚨 Need Admin Power.. You can't use this command.. But you can use in my pm")
        return

    input_str = event.pattern_match.group(1).strip()
    if event.reply_to_msg_id:
        previous_message = await event.get_reply_message()
        text = previous_message.message
        lan = input_str or "en"
    elif "|" in input_str:
        lan, text = input_str.split("|", 1)
    elif input_str:
        lan, text = "en", input_str
    else:
        await event.reply(
            "Invalid Syntax\nFormat `/tts lang | text`\nFor eg: `/tts en | hello`"
        )
        return
    text = (text or "").strip()
    lan = lan.strip() or "en"
    if not text:
        await event.reply("The text is empty.")
        return

    path = os.path.join(tempfile.gettempdir(), f"tts_{event.chat_id}_{event.id}.mp3")

    def _save():
        gTTS(text, tld="com", lang=lan).save(path)

    try:
        await asyncio.get_running_loop().run_in_executor(None, _save)
    except AssertionError:
        await event.reply(
            "The text is empty.\n"
            "Nothing left to speak after pre-precessing, "
            "tokenizing and cleaning."
        )
        return
    except ValueError:
        await event.reply("Language is not supported.")
        return
    except RuntimeError:
        await event.reply("Error loading the languages dictionary.")
        return
    except gTTSError:
        await event.reply("Error in Google Text-to-Speech API request !")
        return
    try:
        await tbot.send_file(event.chat_id, path, voice_note=True, reply_to=event.id)
    finally:
        os.remove(path)


__help__ = """
 • `/tts <lang> | <text>`*:* Converts text to speech (eg: `/tts en | hello`)
 • `/tts <lang>`*:* (as a reply) Reads the replied message aloud
"""
__mod_name__ = "TTS"
