import html

import aiohttp
from bs4 import BeautifulSoup
from IronRobo.events import register

SCORE_FEED = "https://static.cricinfo.com/rss/livescores.xml"


async def is_register_admin(event, user_id):
    try:
        perms = await event.client.get_permissions(event.chat_id, user_id)
    except Exception:
        return False
    return perms.is_admin or perms.is_creator


@register(pattern="^/cs$")
async def cricket_score(event):
    if event.fwd_from:
        return
    if event.is_group and not await is_register_admin(event, event.sender_id):
        await event.reply("🚨 Need Admin Power.. You can't use this command.. But you can use in my pm")
        return
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            async with session.get(SCORE_FEED) as resp:
                page = await resp.text()
    except Exception:
        await event.reply("Cricinfo isn't reachable right now, try again later.")
        return
    soup = BeautifulSoup(page, "xml")
    matches = [m.get_text().strip() for m in soup.find_all("description")]
    matches = [m for m in matches if m and "cricinfo" not in m.lower()]
    if not matches:
        await event.reply("No live matches right now.")
        return
    text = "\n\n".join(html.escape(m) for m in matches[:30])
    await event.reply(
        f"<b><u>Match information gathered successfully</u></b>\n\n<code>{text}</code>",
        parse_mode="html",
    )


__help__ = """
*live cricket score*
 ❍ /cs*:* Latest live scores from cricinfo
"""

__mod_name__ = "Cricket"
