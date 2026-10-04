import base64
import codecs

from IronRobo.events import register

# Simple reversible text scrambling (rot13 + base64). Not real cryptography.


def encrypt(text: str) -> str:
    return base64.urlsafe_b64encode(codecs.encode(text, "rot13").encode()).decode()


def decrypt(text: str) -> str:
    return codecs.decode(base64.urlsafe_b64decode(text.encode()).decode(), "rot13")


async def _get_text(event):
    if event.reply_to_msg_id:
        reply = await event.get_reply_message()
        return reply.text
    return event.pattern_match.group(1)


@register(pattern="^/encrypt ?(.*)")
async def encrypt_cmd(event):
    text = await _get_text(event)
    if not text:
        await event.reply("Give me some text (or reply to a message) to encrypt.")
        return
    await event.reply(f"`{encrypt(text)}`")


@register(pattern="^/decrypt ?(.*)")
async def decrypt_cmd(event):
    text = await _get_text(event)
    if not text:
        await event.reply("Give me some text (or reply to a message) to decrypt.")
        return
    try:
        await event.reply(decrypt(text.strip().strip("`")))
    except Exception:
        await event.reply("That doesn't look like something I encrypted.")


__help__ = """
 • `/encrypt <text>`*:* Scrambles the text (or the replied message)
 • `/decrypt <text>`*:* Turns scrambled text back into the original
"""
__mod_name__ = "Encrypt"
