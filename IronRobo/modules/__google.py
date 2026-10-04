import asyncio
import html
import io
import os
import re
import tempfile
from urllib.parse import quote_plus

import requests
from ddgs import DDGS
from google_play_scraper import search as play_search
from IronRobo import LOGGER
from IronRobo import telethn as tbot
from IronRobo.events import register
from IronRobo.utils.upload import upload_media
from PIL import Image
from telethon import Button

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def _run(func, *args, **kwargs):
    return asyncio.get_running_loop().run_in_executor(None, lambda: func(*args, **kwargs))


@register(pattern="^/google (.*)")
async def google(event):
    if event.fwd_from:
        return
    webevent = await event.reply("searching........")
    match = event.pattern_match.group(1)
    page = 1
    page_match = re.search(r"page=(\d+)", match)
    if page_match:
        page = max(1, int(page_match.group(1)))
        match = match.replace(page_match.group(0), "").strip()
    try:
        results = await _run(DDGS().text, match, max_results=8 * page)
    except Exception as e:
        LOGGER.warning("Web search failed: %s", e)
        await webevent.edit("Search failed, try again later.")
        return
    results = results[8 * (page - 1):]
    if not results:
        await webevent.edit("No results found.")
        return
    msg = ""
    for r in results:
        title = html.escape(r.get("title", ""))
        link = html.escape(r.get("href", ""))
        desc = html.escape(r.get("body", ""))
        msg += f'❍<a href="{link}">{title}</a>\n<b>{desc}</b>\n\n'
    await webevent.edit(
        f"<b>Search Query:</b>\n<code>{html.escape(match)}</code>\n\n<b>Results:</b>\n{msg}",
        link_preview=False,
        parse_mode="html",
    )


def _download_images(query, limit):
    images = []
    for r in DDGS().images(query, max_results=limit * 3, safesearch="moderate"):
        if len(images) >= limit:
            break
        try:
            resp = requests.get(r["image"], headers=HEADERS, timeout=15)
            if not resp.ok:
                continue
            Image.open(io.BytesIO(resp.content)).verify()
        except Exception:
            continue
        f = io.BytesIO(resp.content)
        f.name = f"image{len(images)}.jpg"
        images.append(f)
    return images


@register(pattern="^/img (.*)")
async def img_sampler(event):
    if event.fwd_from:
        return
    query = event.pattern_match.group(1)
    lim = 4
    lim_match = re.search(r"lim=(\d+)", query)
    if lim_match:
        lim = min(10, max(1, int(lim_match.group(1))))
        query = query.replace(lim_match.group(0), "").strip()
    status = await event.reply("`Searching images...`")
    try:
        images = await _run(_download_images, query, lim)
    except Exception as e:
        LOGGER.warning("Image search failed: %s", e)
        images = []
    if not images:
        await status.edit("No images found.")
        return
    await tbot.send_file(event.chat_id, images, reply_to=event.id)
    await status.delete()


def _wallpaper(query):
    results = DDGS().images(f"{query} wallpaper", max_results=15, size="Wallpaper")
    for r in results:
        try:
            resp = requests.get(r["image"], headers=HEADERS, timeout=20)
            if not resp.ok:
                continue
            Image.open(io.BytesIO(resp.content)).verify()
        except Exception:
            continue
        f = io.BytesIO(resp.content)
        f.name = "wallpaper.jpg"
        return f
    return None


@register(pattern="^/wall (.*)")
async def wall(event):
    query = event.pattern_match.group(1).strip()
    status = await event.reply("`Looking for a wallpaper...`")
    try:
        wallpaper = await _run(_wallpaper, query)
    except Exception as e:
        LOGGER.warning("Wallpaper search failed: %s", e)
        wallpaper = None
    if not wallpaper:
        await status.edit("No wallpapers found.")
        return
    await tbot.send_file(event.chat_id, wallpaper, reply_to=event.id)
    wallpaper.seek(0)
    await tbot.send_file(event.chat_id, wallpaper, reply_to=event.id, force_document=True)
    await status.delete()


@register(pattern=r"^/reverse(?: |$)(\d*)")
async def okgoogle(img):
    """Reverse image search: upload the image and link the search engines."""
    message = await img.get_reply_message()
    if not (message and (message.photo or message.sticker or message.document)):
        await img.reply("`Reply to a photo or sticker.`")
        return
    dev = await img.reply("`Processing...`")
    photo = io.BytesIO()
    await tbot.download_media(message, photo)
    try:
        image = Image.open(photo)
    except OSError:
        await dev.edit("`Unsupported file, most likely.`")
        return
    path = os.path.join(tempfile.gettempdir(), f"reverse_{img.chat_id}_{img.id}.png")
    image.save(path, "PNG")
    image.close()
    try:
        url = await _run(upload_media, path)
    finally:
        os.remove(path)
    if not url:
        await dev.edit("`Couldn't upload the image, try again later.`")
        return
    q = quote_plus(url)
    buttons = [
        [Button.url("Google Lens", f"https://lens.google.com/uploadbyurl?url={q}")],
        [Button.url("Bing", f"https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{q}")],
        [Button.url("Yandex", f"https://yandex.com/images/search?rpt=imageview&url={q}")],
    ]
    await dev.delete()
    await img.reply("Search this image on:", buttons=buttons)


@register(pattern="^/app (.*)")
async def apk(e):
    app_name = e.pattern_match.group(1)
    try:
        results = await _run(play_search, app_name, n_hits=1)
    except Exception as err:
        await e.reply("Exception Occured:- " + str(err))
        return
    if not results or not results[0].get("appId"):
        await e.reply("No result found in search. Please enter **Valid app name**")
        return
    app = results[0]
    esc = html.escape
    app_link = f"https://play.google.com/store/apps/details?id={app['appId']}"
    rating = app.get("score")
    app_details = f"<a href='{esc(app.get('icon') or '')}'>📲&#8203;</a>"
    app_details += f" <b>{esc(app.get('title') or app['appId'])}</b>"
    app_details += f"\n\n<code>Developer :</code> {esc(app.get('developer') or '-')}"
    app_details += f"\n<code>Rating :</code> {'⭐ %.1f/5' % rating if rating else 'Not rated'}"
    app_details += f"\n<code>Price :</code> {'Free' if app.get('free', True) else esc(str(app.get('price')))}"
    if app.get("installs"):
        app_details += f"\n<code>Installs :</code> {esc(str(app['installs']))}"
    app_details += f"\n<code>Features :</code> <a href='{app_link}'>View in Play Store</a>"
    await e.reply(app_details, link_preview=True, parse_mode="html")


__mod_name__ = "◎SEARCH"

__help__ = """
 ❍ /google <text>*:* Perform a web search (add `page=2` for more results)
 ❍ /img <text>*:* Search for images and returns them\nFor greater no. of results specify lim, For eg: `/img hello lim=10`
 ❍ /app <appname>*:* Searches for an app in Play Store and returns its details.
 ❍ /reverse: Reverse image search of the photo or sticker it was replied to.
 ❍ /gps <location>*:* Get gps location.
 ❍ /github <username>*:* Get information about a GitHub user.
 ❍ /country <country name>*:* Gathering info about given country
 ❍ /imdb <Movie name>*:* Get full info about a movie with imdb.com
"""
