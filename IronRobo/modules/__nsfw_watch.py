from IronRobo import telethn as tbot
from IronRobo.events import register
from IronRobo.helper_extra.badmedia import is_nsfw
from IronRobo.modules.sql_extended.nsfw_watch_sql import (
    add_nsfwatch,
    is_nsfwatch_indb,
    rmnsfwatch,
)
from telethon import events
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights

MUTE_RIGHTS = ChatBannedRights(until_date=None, send_messages=True)


async def can_change_info(event):
    try:
        perms = await event.client.get_permissions(event.chat_id, event.sender_id)
    except Exception:
        return False
    return perms.is_creator or (perms.is_admin and perms.change_info)


async def is_admin(event, user_id):
    try:
        perms = await event.client.get_permissions(event.chat_id, user_id)
    except Exception:
        return False
    return perms.is_admin or perms.is_creator


@register(pattern="^/nsfw$")
async def nsfw(event):
    if event.is_private:
        return
    if is_nsfwatch_indb(str(event.chat_id)):
        await event.reply("`This Chat has Enabled NSFW watch`")
    else:
        await event.reply("`NSfw Watch is off for this chat`")


async def enable_watch(event):
    if is_nsfwatch_indb(str(event.chat_id)):
        await event.reply("`This Chat Has Already Enabled Nsfw Watch.`")
        return
    add_nsfwatch(str(event.chat_id))
    await event.reply(
        f"**Added Chat {event.chat.title} With Id {event.chat_id} To Database. This Groups Nsfw Contents Will Be Deleted**"
    )


async def disable_watch(event):
    if not is_nsfwatch_indb(str(event.chat_id)):
        await event.reply("This Chat Has Not Enabled Nsfw Watch.")
        return
    rmnsfwatch(str(event.chat_id))
    await event.reply(
        f"**Removed Chat {event.chat.title} With Id {event.chat_id} From Nsfw Watch**"
    )


@register(pattern="^/addnsfw$")
async def nsfw_watch(event):
    if event.is_private:
        return
    if not await can_change_info(event):
        await event.reply("`You need the 'change group info' right to do this!`")
        return
    await enable_watch(event)


@register(pattern="^/rmnsfw$")
async def disable_nsfw(event):
    if event.is_private:
        return
    if not await can_change_info(event):
        await event.reply("`You need the 'change group info' right to do this!`")
        return
    await disable_watch(event)


@tbot.on(events.NewMessage(incoming=True))
async def ws(event):
    if event.is_private or not event.media:
        return
    if not (event.gif or event.video or event.video_note or event.photo or event.sticker):
        return
    if not is_nsfwatch_indb(str(event.chat_id)):
        return
    if await is_admin(event, event.sender_id):
        return
    if not await is_nsfw(event):
        return
    his_id = event.sender_id
    try:
        await event.delete()
    except Exception:
        return
    try:
        await event.client(EditBannedRequest(event.chat_id, his_id, MUTE_RIGHTS))
        action = "muted"
    except Exception:
        action = "warned"
    try:
        sender = await event.get_sender()
        name = getattr(sender, "first_name", None) or getattr(sender, "title", "user")
        await event.respond(
            f"**#NSFW_WATCH**\n[{name}](tg://user?id={his_id}) sent NSFW content, "
            f"the message was deleted and the sender was {action}."
        )
    except Exception:
        pass


__help__ = """
*NSFW Watch:*
 • `/nsfw`*:* Shows whether NSFW watch is on in this chat
 • `/addnsfw`*:* Delete NSFW photos, stickers and videos and mute the sender
 • `/rmnsfw`*:* Turn NSFW watch off
"""
__mod_name__ = "NSFW Watch"
