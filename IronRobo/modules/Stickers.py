import io
import json
import math
import os
import textwrap

import cloudscraper
import requests
from bs4 import BeautifulSoup as bs
from html import escape
from PIL import Image, ImageDraw, ImageFont
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html

from IronRobo import LOGGER, dispatcher
from IronRobo import telethn as bot
from IronRobo.events import register as Cutiepii
from IronRobo.modules.disable import DisableAbleCommandHandler

combot_stickers_url = "https://combot.org/telegram/stickers?q="
MAX_STICKERS = 120


def stickerid(update: Update, context: CallbackContext):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.sticker:
        update.effective_message.reply_text(
            "Hello "
            + f"{mention_html(msg.from_user.id, msg.from_user.first_name)}"
            + ", The sticker id you are replying is :\n <code>"
            + escape(msg.reply_to_message.sticker.file_id)
            + "</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        update.effective_message.reply_text(
            "Hello "
            + f"{mention_html(msg.from_user.id, msg.from_user.first_name)}"
            + ", Please reply to sticker message to get id sticker",
            parse_mode=ParseMode.HTML,
        )


def cb_sticker(update: Update, context: CallbackContext):
    msg = update.effective_message
    split = msg.text.split(" ", 1)
    if len(split) == 1:
        msg.reply_text("Provide some name to search for pack.")
        return
    try:
        scraper = cloudscraper.create_scraper()
        text = scraper.get(combot_stickers_url + split[1], timeout=20).text
    except Exception as e:
        LOGGER.warning("Combot sticker search failed: %s", e)
        msg.reply_text("The sticker catalogue isn't reachable right now, try again later.")
        return
    soup = bs(text, "lxml")
    results = soup.find_all("a", {"class": "sticker-pack__btn"})
    titles = soup.find_all("div", "sticker-pack__title")
    if not results:
        msg.reply_text("No results found :(.")
        return
    reply = f"Stickers for <b>{escape(split[1])}</b>:"
    for result, title in zip(results, titles):
        link = result["href"]
        reply += f'\n• <a href="{escape(link)}">{escape(title.get_text())}</a>'
    msg.reply_text(reply, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def getsticker(update: Update, context: CallbackContext):
    msg = update.effective_message
    reply = msg.reply_to_message
    if not (reply and reply.sticker):
        msg.reply_text("Please reply to a sticker for me to upload its PNG.")
        return
    sticker = reply.sticker
    data = io.BytesIO()
    context.bot.get_file(sticker.file_id).download(out=data)
    data.seek(0)
    if sticker.is_animated or sticker.is_video:
        data.name = "sticker.tgs" if sticker.is_animated else "sticker.webm"
    else:
        png = io.BytesIO()
        Image.open(data).save(png, "PNG")
        png.seek(0)
        data = png
        data.name = "sticker.png"
    context.bot.send_document(update.effective_chat.id, document=data)


class StickerError(Exception):
    def __init__(self, description):
        super().__init__(description)
        self.description = description


def _api(bot, method, data, files=None):
    """Call the Bot API directly.

    python-telegram-bot 13 predates the current sticker API (InputSticker,
    mixed-format packs), so sticker set calls are made by hand.
    """
    r = requests.post(f"{bot.base_url}/{method}", data=data, files=files, timeout=60)
    try:
        result = r.json()
    except ValueError:
        raise StickerError(f"Bad response from Telegram ({r.status_code})")
    if not result.get("ok"):
        raise StickerError(result.get("description", "Unknown error"))
    return result["result"]


def _pack_name(bot, user_id, packnum):
    if packnum == 0:
        return f"f{user_id}_by_{bot.username}"
    return f"f{packnum}_{user_id}_by_{bot.username}"


def _find_pack(bot, user_id):
    """Return (packname, packnum, exists) for the first pack that has room."""
    packnum = 0
    while True:
        packname = _pack_name(bot, user_id, packnum)
        try:
            stickerset = _api(bot, "getStickerSet", {"name": packname})
        except StickerError as e:
            if "STICKERSET_INVALID" in e.description.upper():
                return packname, packnum, False
            raise
        if len(stickerset.get("stickers", [])) < MAX_STICKERS:
            return packname, packnum, True
        packnum += 1


def _resize_to_png(raw: bytes) -> io.BytesIO:
    im = Image.open(io.BytesIO(raw))
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA")
    # one side must be exactly 512px, the other 512px or less
    scale = 512 / max(im.width, im.height)
    im = im.resize(
        (max(1, math.floor(im.width * scale)), max(1, math.floor(im.height * scale))),
        Image.LANCZOS,
    )
    out = io.BytesIO()
    im.save(out, "PNG")
    out.seek(0)
    return out


def _start_pm_markup(bot):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="Start", url=f"https://t.me/{bot.username}")]]
    )


def kang(update: Update, context: CallbackContext):
    msg = update.effective_message
    user = update.effective_user
    args = context.args
    bot = context.bot
    reply = msg.reply_to_message

    files = None
    sticker_emoji = None
    if reply and reply.sticker:
        st = reply.sticker
        fmt = "animated" if st.is_animated else "video" if st.is_video else "static"
        sticker_input = st.file_id
        sticker_emoji = st.emoji
    elif reply and (reply.photo or reply.document):
        if reply.document and not (reply.document.mime_type or "").startswith("image/"):
            msg.reply_text("Yea, I can't kang that.")
            return
        file_id = reply.photo[-1].file_id if reply.photo else reply.document.file_id
        raw = io.BytesIO()
        bot.get_file(file_id).download(out=raw)
        try:
            png = _resize_to_png(raw.getvalue())
        except OSError:
            msg.reply_text("I can only kang images m8.")
            return
        fmt, sticker_input, files = "static", "attach://sticker", {"sticker": ("sticker.png", png)}
    elif args and args[0].startswith(("http://", "https://")):
        try:
            raw = requests.get(args[0], timeout=30).content
            png = _resize_to_png(raw)
        except (requests.RequestException, OSError):
            msg.reply_text("I couldn't get an image from that link.")
            return
        fmt, sticker_input, files = "static", "attach://sticker", {"sticker": ("sticker.png", png)}
        args = args[1:]
    else:
        try:
            packname, packnum, exists = _find_pack(bot, user.id)
        except StickerError:
            packname, packnum, exists = _pack_name(bot, user.id, 0), 0, False
        if not exists and packnum == 0:
            msg.reply_text("Please reply to a sticker, or image to kang it! You don't have a pack yet.")
            return
        packs = "Please reply to a sticker, or image to kang it!\nOh, by the way. here are your packs:\n"
        for i in range(packnum + (1 if exists else 0)):
            packs += f"[pack{i or ''}](t.me/addstickers/{_pack_name(bot, user.id, i)})\n"
        msg.reply_text(packs, parse_mode=ParseMode.MARKDOWN)
        return

    if args:
        sticker_emoji = args[0]
    sticker_emoji = sticker_emoji or "👀"
    input_sticker = {
        "sticker": sticker_input,
        "format": fmt,
        "emoji_list": [sticker_emoji],
    }

    try:
        packname, packnum, exists = _find_pack(bot, user.id)
        if exists:
            _api(
                bot,
                "addStickerToSet",
                {"user_id": user.id, "name": packname, "sticker": json.dumps(input_sticker)},
                files,
            )
        else:
            extra_version = f" {packnum}" if packnum > 0 else ""
            _api(
                bot,
                "createNewStickerSet",
                {
                    "user_id": user.id,
                    "name": packname,
                    "title": f"{user.first_name[:50]}'s kang pack{extra_version}",
                    "stickers": json.dumps([input_sticker]),
                },
                files,
            )
    except StickerError as e:
        desc = e.description
        if "PEER_ID_INVALID" in desc.upper() or "blocked" in desc or "chat not found" in desc:
            msg.reply_text("Contact me in PM first.", reply_markup=_start_pm_markup(bot))
        elif "emoji" in desc.lower():
            msg.reply_text("Invalid emoji(s).")
        elif "too much" in desc.lower() or "STICKERS_TOO_MUCH" in desc.upper():
            msg.reply_text("Max packsize reached. Press F to pay respecc.")
        else:
            LOGGER.warning("Kang failed: %s", desc)
            msg.reply_text(f"Failed to kang that: {desc}")
        return

    action = "added to" if exists else "added to your new"
    msg.reply_text(
        f"Sticker successfully {action} [pack](t.me/addstickers/{packname})"
        + f"\nEmoji is: {sticker_emoji}",
        parse_mode=ParseMode.MARKDOWN,
    )


def delsticker(update, context):
    msg = update.effective_message
    if not (msg.reply_to_message and msg.reply_to_message.sticker):
        msg.reply_text("Please reply to the sticker which you want to delete from your pack")
        return
    sticker = msg.reply_to_message.sticker
    set_name = sticker.set_name or ""
    if not set_name.endswith(f"_by_{context.bot.username}") or str(
        update.effective_user.id
    ) not in set_name:
        msg.reply_text("Maybe the sticker pack is not yours or the pack was not made by me!")
        return
    try:
        _api(context.bot, "deleteStickerFromSet", {"sticker": sticker.file_id})
        msg.reply_text(
            "Deleted That Sticker from your Pack!\nRemove and Re-Add the Pack to see the changes."
        )
    except StickerError as e:
        msg.reply_text(f"Couldn't delete it: {e.description}")


Credit = "This Plugin Made by Kittu (@A_viyu), if you're using this code in your bot. there is no issue but don't remove this line" 


@Cutiepii(pattern="^/mmf ?(.*)")
async def handler(event):
    if event.fwd_from:
        return
    if not event.reply_to_msg_id:
        await event.reply("Reply to an image or a sticker to memeify it!")
        return
    reply_message = await event.get_reply_message()
    if not (reply_message.photo or reply_message.sticker or (
        reply_message.document and (reply_message.file.mime_type or "").startswith("image/")
    )):
        await event.reply("Reply to an image or a static sticker!")
        return
    text = str(event.pattern_match.group(1)).strip()
    if len(text) < 1:
        await event.reply("You might want to try `/mmf text` (use `;` to split top;bottom text)")
        return
    msg = await event.reply("Memifying this image! Please wait")
    file = await bot.download_media(reply_message)
    try:
        meme = await drawText(file, text)
    except Exception:
        if file and os.path.exists(file):
            os.remove(file)
        await msg.edit("I can't memify that (animated and video stickers aren't supported).")
        return
    await bot.send_file(event.chat_id, file=meme, force_document=False)
    await msg.delete()
    os.remove(meme)


def _text_size(draw, text, font):
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top


# Taken from https://github.com/UsergeTeam/Userge-Plugins/blob/master/plugins/memify.py#L64
# Maybe replyed to suit the needs of this module

async def drawText(image_path, text):
    img = Image.open(image_path).convert("RGBA")
    os.remove(image_path)
    shadowcolor = "black"
    i_width, i_height = img.size
    fnt = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "resources",
        "ArmWrestler.ttf",
    )
    m_font = ImageFont.truetype(fnt, int((70 / 640) * i_width))
    if ";" in text:
        upper_text, lower_text = text.split(";", 1)
    else:
        upper_text = text
        lower_text = ''
    draw = ImageDraw.Draw(img)
    current_h, pad = 10, 5
    if upper_text:
        for u_text in textwrap.wrap(upper_text, width=15):
            u_width, u_height = _text_size(draw, u_text, m_font)
            draw.text(xy=(((i_width - u_width) / 2) - 2, int((current_h / 640)

                                                             * i_width)), text=u_text, font=m_font, fill=(0, 0, 0))

            draw.text(xy=(((i_width - u_width) / 2) + 2, int((current_h / 640)

                                                             * i_width)), text=u_text, font=m_font, fill=(0, 0, 0))
            draw.text(xy=((i_width - u_width) / 2,
                          int(((current_h / 640) * i_width)) - 2),

                      text=u_text,
                      font=m_font,
                      fill=(0,
                            0,
                            0))

            draw.text(xy=(((i_width - u_width) / 2),
                          int(((current_h / 640) * i_width)) + 2),

                      text=u_text,
                      font=m_font,
                      fill=(0,
                            0,
                            0))



            draw.text(xy=((i_width - u_width) / 2, int((current_h / 640)

                                                       * i_width)), text=u_text, font=m_font, fill=(255, 255, 255))

            current_h += u_height + pad

    if lower_text:
        for l_text in textwrap.wrap(lower_text, width=15):
            u_width, u_height = _text_size(draw, l_text, m_font)
            draw.text(
                xy=(((i_width - u_width) / 2) - 2, i_height -
                    u_height - int((20 / 640) * i_width)),
                text=l_text, font=m_font, fill=(0, 0, 0))
            draw.text(
                xy=(((i_width - u_width) / 2) + 2, i_height -
                    u_height - int((20 / 640) * i_width)),
                text=l_text, font=m_font, fill=(0, 0, 0))
            draw.text(
                xy=((i_width - u_width) / 2, (i_height -
                                              u_height - int((20 / 640) * i_width)) - 2),
                text=l_text, font=m_font, fill=(0, 0, 0))

            draw.text(
                xy=((i_width - u_width) / 2, (i_height -

                                              u_height - int((20 / 640) * i_width)) + 2),
                text=l_text, font=m_font, fill=(0, 0, 0))


            draw.text(
                xy=((i_width - u_width) / 2, i_height -
                    u_height - int((20 / 640) * i_width)),
                text=l_text, font=m_font, fill=(255, 255, 255))
            current_h += u_height + pad          
    image_name = f"memify_{os.getpid()}_{id(img)}.webp"
    webp_file = os.path.join(image_name)
    img.save(webp_file, "webp")
    return webp_file



__help__ = """
  ➢ `/stickerid` : reply to a sticker to me to tell you its file ID.
  ➢ `/getsticker` : reply to a sticker to me to upload its raw PNG file.
  ➢ `/kang` : reply to a sticker, photo or image file to add it to your pack (you can add an emoji after the command).
  ➢ `/delkang` : reply to a Sticker to remove it from your pack
  ➢ `/mmf` : memefiy any sticker and image.
  ➢ `/stickers` : Find stickers for given term on combot sticker catalogue
"""

__mod_name__ = "Stickers"
STICKERID_HANDLER = DisableAbleCommandHandler("stickerid", stickerid, run_async=True)
GETSTICKER_HANDLER = DisableAbleCommandHandler("getsticker", getsticker, run_async=True)
KANG_HANDLER = DisableAbleCommandHandler(
    ["kang", "steal"], kang, admin_ok=True, run_async=True
)
DELKANG_HANDLER = DisableAbleCommandHandler(
    ["delsticker", "delkang"], delsticker, admin_ok=True, run_async=True
)
STICKERS_HANDLER = DisableAbleCommandHandler("stickers", cb_sticker, run_async=True)

dispatcher.add_handler(STICKERS_HANDLER)
dispatcher.add_handler(STICKERID_HANDLER)
dispatcher.add_handler(GETSTICKER_HANDLER)
dispatcher.add_handler(KANG_HANDLER)
dispatcher.add_handler(DELKANG_HANDLER)
