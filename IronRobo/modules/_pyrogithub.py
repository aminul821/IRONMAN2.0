import html

import aiohttp
from pyrogram import filters
from IronRobo import pbot
from IronRobo.pyrogramee.errors import capture_err


@pbot.on_message(filters.command(["github", "git"]))
@capture_err
async def github(_, message):
    if len(message.command) != 2:
        await message.reply_text("Usage: /github <username>")
        return
    username = message.command[1]
    url = f"https://api.github.com/users/{username}"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        async with session.get(url, headers={"Accept": "application/vnd.github+json"}) as request:
            if request.status == 404:
                await message.reply_text("User not found.")
                return
            if request.status != 200:
                await message.reply_text(f"GitHub returned an error ({request.status}).")
                return
            result = await request.json()

    def f(key):
        value = result.get(key)
        return html.escape(str(value)) if value not in (None, "") else "-"

    caption = (
        f"<b>Info Of {f('name') if result.get('name') else html.escape(username)}</b>\n"
        f"<b>Username:</b> <code>{f('login')}</code>\n"
        f"<b>Bio:</b> <code>{f('bio')}</code>\n"
        f"<b>Profile Link:</b> <a href=\"{f('html_url')}\">Here</a>\n"
        f"<b>Company:</b> <code>{f('company')}</code>\n"
        f"<b>Created On:</b> <code>{f('created_at')}</code>\n"
        f"<b>Repositories:</b> <code>{f('public_repos')}</code>\n"
        f"<b>Blog:</b> <code>{f('blog')}</code>\n"
        f"<b>Location:</b> <code>{f('location')}</code>\n"
        f"<b>Followers:</b> <code>{f('followers')}</code>\n"
        f"<b>Following:</b> <code>{f('following')}</code>"
    )
    await message.reply_photo(photo=result["avatar_url"], caption=caption, parse_mode="html")


__mod_name__ = "Github"
