import asyncio

from pyrogram import filters

from IronRobo import pbot
from IronRobo.pyrogramee.pluginhelpers import admins_only, get_text

MENTIONS_PER_MESSAGE = 5


@pbot.on_message(filters.command(["tagall", "all"]) & filters.group & ~filters.edited & ~filters.bot)
@admins_only
async def tagall(client, message):
    sh = get_text(message) or "Hi!"
    batch = []
    async for member in client.iter_chat_members(message.chat.id):
        if member.user.is_bot or member.user.is_deleted:
            continue
        batch.append(member.user.mention)
        if len(batch) == MENTIONS_PER_MESSAGE:
            await client.send_message(message.chat.id, f"<b>{sh}</b>\n" + " ".join(batch), parse_mode="html")
            batch = []
            await asyncio.sleep(2)
    if batch:
        await client.send_message(message.chat.id, f"<b>{sh}</b>\n" + " ".join(batch), parse_mode="html")


__mod_name__ = "Tagall"
__help__ = """
 • `/tagall <text>`*:* Tags everyone in the chat (admins only)
"""
