import asyncio
import glob
import os
import random
import tempfile

from IronRobo import telethn as tbot
from IronRobo.events import register
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKGROUNDS = os.path.join(ROOT, "resources", "extras", "*")
FONTS = os.path.join(ROOT, "resources", "fonts", "*")


def make_logo(text, path):
    img = Image.open(random.choice(glob.glob(BACKGROUNDS))).convert("RGB")
    draw = ImageDraw.Draw(img)
    image_width, image_height = img.size
    font_size = 140
    font = ImageFont.truetype(random.choice(glob.glob(FONTS)), font_size)
    # shrink long names so they fit on the picture
    while font_size > 20:
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font, stroke_width=19)
        if right - left <= image_width * 0.9:
            break
        font_size -= 10
        font = ImageFont.truetype(font.path, font_size)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    w, h = right - left, bottom - top
    h += int(h * 0.21)
    x = (image_width - w) / 2
    y = (image_height - h) / 1.5
    draw.text((x, y), text, font=font, fill="white", stroke_width=19, stroke_fill="black")
    img.save(path, "png")


@register(pattern="^/logo ?(.*)")
async def lego(event):
    text = event.pattern_match.group(1).strip()
    if not text:
        await event.reply("Provide some text to draw! Example: /logo <your name>")
        return
    xnxx = await event.reply("Preparing Logo")
    path = os.path.join(tempfile.gettempdir(), f"logo_{event.chat_id}_{event.id}.png")
    try:
        await asyncio.get_running_loop().run_in_executor(None, make_logo, text, path)
        await xnxx.edit("Uploading")
        await tbot.send_file(event.chat_id, path, caption="Made by Ironman 🔥", reply_to=event.id)
        await xnxx.delete()
    except Exception as e:
        await xnxx.edit(f"Couldn't make the logo: {e}")
    finally:
        if os.path.exists(path):
            os.remove(path)


__mod_name__ = "Logo"
__help__ = """
 • `/logo <name>`*:* Creates a logo with your name on a random background
"""
