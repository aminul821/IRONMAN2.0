import asyncio
import html
import json
import re
from urllib.parse import quote

import requests
from IronRobo.events import register

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def _search(query):
    q = query.strip().lower()
    url = f"https://v3.sg.media-imdb.com/suggestion/{quote(q[0])}/{quote(q)}.json"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    for item in r.json().get("d", []):
        if item.get("id", "").startswith("tt"):
            return item
    return None


def _details(imdb_id):
    r = requests.get(f"https://www.imdb.com/title/{imdb_id}/", headers=HEADERS, timeout=20)
    r.raise_for_status()
    match = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', r.text, re.S
    )
    return json.loads(match.group(1)) if match else {}


def _names(value, limit=3):
    if not value:
        return "Not available"
    if isinstance(value, dict):
        value = [value]
    return ", ".join(v.get("name", "") for v in value[:limit] if v.get("name")) or "Not available"


def _lookup(query):
    item = _search(query)
    if not item:
        return None
    try:
        data = _details(item["id"])
    except requests.RequestException:
        data = {}
    return item, data


@register(pattern="^/imdb (.*)")
async def imdb(e):
    if e.fwd_from:
        return
    movie_name = e.pattern_match.group(1).strip()
    try:
        result = await asyncio.get_running_loop().run_in_executor(None, _lookup, movie_name)
    except requests.RequestException:
        await e.reply("IMDb isn't reachable right now, try again later.")
        return
    if not result:
        await e.reply("Plox enter **Valid movie name** kthx")
        return
    item, data = result
    esc = html.escape
    title = data.get("name") or item.get("l", "Unknown")
    year = item.get("y", "")
    rating = data.get("aggregateRating", {}).get("ratingValue", "Not available")
    genres = data.get("genre") or []
    if isinstance(genres, str):
        genres = [genres]
    poster = data.get("image") or (item.get("i") or {}).get("imageUrl", "")
    link = f"https://www.imdb.com/title/{item['id']}/"
    text = (
        (f'<a href="{esc(poster)}">&#8203;</a>' if poster else "")
        + f"<b>Title : </b><code>{esc(html.unescape(str(title)))}</code> ({esc(str(year))})\n"
        + f"<b>Rating : </b><code>{esc(str(rating))}</code>\n"
        + f"<b>Genre : </b><code>{esc(', '.join(genres) or 'Not available')}</code>\n"
        + f"<b>Director : </b><code>{esc(html.unescape(_names(data.get('director'))))}</code>\n"
        + f"<b>Stars : </b><code>{esc(html.unescape(_names(data.get('actor')) if data.get('actor') else item.get('s', 'Not available')))}</code>\n"
        + f"<b>IMDB Url : </b>{esc(link)}\n"
        + f"<b>Story Line : </b>{esc(html.unescape(data.get('description', 'Not available')))}"
    )
    await e.reply(text, link_preview=bool(poster), parse_mode="html")


__help__ = """
 • `/imdb <movie or series name>`*:* Get details about a movie or series from IMDb
"""
__mod_name__ = "IMDb"
