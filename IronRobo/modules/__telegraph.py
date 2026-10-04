import asyncio
import os
import tempfile
from datetime import datetime

from IronRobo import telethn as tbot
from IronRobo.events import register
from IronRobo.utils.upload import upload_media
from PIL import Image
from telegraph import Telegraph

_telegraph = None


def get_telegraph():
    global _telegraph
    if _telegraph is None:
        telegraph = Telegraph()
        telegraph.create_account(short_name="Ironman")
        _telegraph = telegraph
    return _telegraph


def resize_image(image):
    im = Image.open(image)
    new_path = os.path.splitext(image)[0] + ".png"
    im.save(new_path, "PNG")
    os.remove(image)
    return new_path


@register(pattern="^/t(m|xt) ?(.*)")
async def telegraph_cmd(event):
    if event.fwd_from:
        return
    if not event.reply_to_msg_id:
        await event.reply("Reply to a message to get a permanent link.")
        return
    optional_title = event.pattern_match.group(2)
    start = datetime.now()
    r_message = await event.get_reply_message()
    input_str = event.pattern_match.group(1)
    loop = asyncio.get_running_loop()
    tmpdir = tempfile.mkdtemp(prefix="tgph_")
    try:
        if input_str == "m":
            if not r_message.media:
                await event.reply("Reply to a photo, video, gif or file.")
                return
            h = await event.reply("`Uploading...`")
            downloaded_file_name = await tbot.download_media(r_message, tmpdir)
            if downloaded_file_name.endswith(".webp"):
                downloaded_file_name = resize_image(downloaded_file_name)
            url = await loop.run_in_executor(None, upload_media, downloaded_file_name)
            if not url:
                await h.edit("Upload failed, try again later.")
                return
            ms = (datetime.now() - start).seconds
            await h.edit(f"Uploaded to {url} in {ms} seconds.", link_preview=True)
        else:
            user_object = await r_message.get_sender()
            title_of_page = getattr(user_object, "first_name", None) or "Ironman"
            if optional_title:
                title_of_page = optional_title
            page_content = r_message.message or ""
            if r_message.media:
                if page_content:
                    title_of_page = page_content[:100]
                downloaded_file_name = await tbot.download_media(r_message, tmpdir)
                with open(downloaded_file_name, "rb") as fd:
                    for m in fd.readlines():
                        page_content += m.decode("UTF-8", errors="ignore") + "\n"
            if not page_content:
                await event.reply("There's no text to paste!")
                return
            page_content = (
                page_content.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
            )
            response = await loop.run_in_executor(
                None,
                lambda: get_telegraph().create_page(
                    title_of_page, html_content=page_content
                ),
            )
            ms = (datetime.now() - start).seconds
            await event.reply(
                "Pasted to https://telegra.ph/{} in {} seconds.".format(
                    response["path"], ms
                ),
                link_preview=True,
            )
    finally:
        for f in os.listdir(tmpdir):
            os.remove(os.path.join(tmpdir, f))
        os.rmdir(tmpdir)


__help__ = """
 • `/tm`*:* Reply to a photo/video/file to upload it and get a link
 • `/txt <title>`*:* Reply to a text message (or a text file) to paste it to telegra.ph
"""
__mod_name__ = "Telegraph"
