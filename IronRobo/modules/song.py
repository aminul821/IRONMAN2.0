import asyncio
import html
import os
import shutil
import tempfile
import time

import lyricsgenius
import requests
from pyrogram import filters
from pyrogram.types import Message
from yt_dlp import YoutubeDL

from IronRobo import GENIUS_API_TOKEN, LOGGER, pbot
from IronRobo.pyrogramee.pluginshelper import get_text, progress

# Optional: a Netscape cookies.txt exported from a logged-in YouTube session.
# Servers in data centres are often asked to "sign in to confirm you're not a
# bot"; cookies fix that.
YT_COOKIES = os.environ.get("YT_COOKIES_FILE", "")
MAX_AUDIO_DURATION = 2 * 60 * 60  # seconds
MAX_VIDEO_DURATION = 30 * 60  # seconds

AUDIO_FORMAT = "bestaudio[ext=m4a]/bestaudio"
VIDEO_FORMAT = "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b[height<=720]/b"


def _ydl_opts(**extra):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "logtostderr": False,
    }
    if YT_COOKIES and os.path.exists(YT_COOKIES):
        opts["cookiefile"] = YT_COOKIES
    opts.update(extra)
    return opts


def _search(query):
    """Return the info dict of the first YouTube result (or of a direct link)."""
    target = query if query.startswith(("http://", "https://")) else f"ytsearch1:{query}"
    with YoutubeDL(_ydl_opts(extract_flat="in_playlist")) as ydl:
        info = ydl.extract_info(target, download=False)
    if info and info.get("entries") is not None:
        entries = [e for e in info["entries"] if e]
        if not entries:
            return None
        info = entries[0]
    return info


def _download(url, fmt, workdir, merge_mp4=False):
    opts = _ydl_opts(
        format=fmt,
        outtmpl=os.path.join(workdir, "%(id)s.%(ext)s"),
        writethumbnail=False,
    )
    if merge_mp4:
        opts["merge_output_format"] = "mp4"
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
    if merge_mp4 and not os.path.exists(path):
        path = os.path.splitext(path)[0] + ".mp4"
    return info, path


def _fetch_thumb(video_id, workdir):
    try:
        r = requests.get(f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg", timeout=15)
        if r.ok:
            path = os.path.join(workdir, "thumb.jpg")
            with open(path, "wb") as f:
                f.write(r.content)
            return path
    except requests.RequestException:
        pass
    return None


async def _youtube(client, message: Message, video: bool):
    query = get_text(message)
    if not query:
        await message.reply_text(
            f"Give me a song name or a link, e.g. `/{message.command[0]} Faded Alan Walker`"
        )
        return
    status = await message.reply_text(f"🔎 Searching for `{query}`...")
    loop = asyncio.get_running_loop()
    workdir = tempfile.mkdtemp(prefix="song_")
    try:
        try:
            info = await loop.run_in_executor(None, _search, query)
        except Exception as e:
            LOGGER.warning("YouTube search failed: %s", e)
            info = None
        if not info:
            await status.edit("✖️ Found Nothing. Try another keyword or spell it properly.")
            return

        url = info.get("webpage_url") or info.get("url")
        if not url or not url.startswith("http"):
            url = f"https://www.youtube.com/watch?v={info['id']}"
        duration = int(info.get("duration") or 0)
        limit = MAX_VIDEO_DURATION if video else MAX_AUDIO_DURATION
        if duration > limit:
            await status.edit(f"That's too long! The limit is {limit // 60} minutes.")
            return

        await status.edit("`Downloading... Please wait ⏱`")
        try:
            data, path = await loop.run_in_executor(
                None,
                _download,
                url,
                VIDEO_FORMAT if video else AUDIO_FORMAT,
                workdir,
                video,
            )
        except Exception as e:
            LOGGER.warning("yt-dlp download failed: %s", e)
            await status.edit(
                f"**Failed To Download**\n`{html.escape(str(e))[:500]}`"
            )
            return

        thumb = await loop.run_in_executor(None, _fetch_thumb, data["id"], workdir)
        title = data.get("title") or "Unknown"
        link = data.get("webpage_url") or url
        caption = (
            f"🎙 **Title**: [{title[:60]}]({link})\n"
            f"🎬 **Channel**: `{data.get('uploader') or data.get('channel') or '-'}`\n"
            f"⏱️ **Duration**: `{time.strftime('%H:%M:%S', time.gmtime(int(data.get('duration') or 0)))}`\n"
            f"📤 **Requested by**: {message.from_user.mention if message.from_user else 'Anonymous'}"
        )
        c_time = time.time()
        await status.edit("`Uploading...`")
        if video:
            await client.send_video(
                message.chat.id,
                video=path,
                duration=int(data.get("duration") or 0),
                file_name=f"{title}.mp4",
                thumb=thumb,
                caption=caption,
                supports_streaming=True,
                progress=progress,
                progress_args=(status, c_time, "`Uploading video...`", title),
            )
        else:
            await client.send_audio(
                message.chat.id,
                audio=path,
                duration=int(data.get("duration") or 0),
                title=title,
                performer=data.get("uploader") or data.get("channel"),
                thumb=thumb,
                caption=caption,
                progress=progress,
                progress_args=(status, c_time, "`Uploading song...`", title),
            )
        await status.delete()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pbot.on_message(filters.command(["song", "music", "saavn", "deezer", "dsong"]))
async def song(client, message: Message):
    await _youtube(client, message, video=False)


@pbot.on_message(filters.command(["vsong", "video"]))
async def vsong(client, message: Message):
    await _youtube(client, message, video=True)


def _genius_lyrics(query):
    genius = lyricsgenius.Genius(
        GENIUS_API_TOKEN, verbose=False, remove_section_headers=False, timeout=20
    )
    if " - " in query:
        artist, title = [x.strip() for x in query.split(" - ", 1)]
        found = genius.search_song(title, artist)
    else:
        found = genius.search_song(query)
    if not found:
        return None, None
    return f"{found.artist} - {found.title}", found.lyrics


def _lyrics_ovh(query):
    if " - " not in query:
        return None, None
    artist, title = [x.strip() for x in query.split(" - ", 1)]
    r = requests.get(f"https://api.lyrics.ovh/v1/{artist}/{title}", timeout=20)
    if not r.ok:
        return None, None
    lyrics = r.json().get("lyrics")
    return (f"{artist} - {title}", lyrics) if lyrics else (None, None)


@pbot.on_message(filters.command(["lyric", "lyrics", "glyric", "glyrics"]))
async def lyrics(client, message: Message):
    query = get_text(message)
    if not query:
        await message.reply_text(
            "Usage: `/lyrics <artist> - <song>`\neg: `/lyrics Nicki Minaj - Super Bass`"
        )
        return
    status = await message.reply_text(f"`Searching lyrics for {query}...`")
    loop = asyncio.get_running_loop()
    name, text = None, None
    try:
        if GENIUS_API_TOKEN:
            name, text = await loop.run_in_executor(None, _genius_lyrics, query)
        if not text:
            name, text = await loop.run_in_executor(None, _lyrics_ovh, query)
    except Exception as e:
        LOGGER.warning("Lyrics lookup failed: %s", e)
    if not text:
        hint = "" if " - " in query else "\nTry `/lyrics <artist> - <song>`."
        await status.edit(f"Lyrics for **{query}** not found!{hint}")
        return
    reply = f"**{name}**\n\n{text}"
    if len(reply) > 4000:
        path = os.path.join(tempfile.gettempdir(), f"lyrics_{message.message_id}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{name}\n\n{text}")
        await client.send_document(message.chat.id, path, caption=name)
        os.remove(path)
        await status.delete()
    else:
        await status.edit(reply, disable_web_page_preview=True)


__mod_name__ = "Music"

__help__ = """
 ❍ /song <song name or link>*:* Uploads the song from YouTube in the best quality available
 💡Ex: `/song Faded Alan Walker` (`/music`, `/saavn` and `/deezer` do the same)
 ❍ /video <song name or link>*:* Uploads the video (up to 30 minutes)
 ❍ /lyrics <artist> - <song>*:* Finds the lyrics of a song
"""
