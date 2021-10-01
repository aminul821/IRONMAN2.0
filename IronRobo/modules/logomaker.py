
from IronRobo.events import register
from IronRobo import OWNER_ID
from IronRobo import telethn as tbot
import os 
from PIL import Image, ImageDraw, ImageFont
import shutil 
import random, re
import glob
import time
from telethon.tl.types import InputMessagesFilterPhotos

@register(pattern="^/logo ?(.*)")
async def lego(event):
 quew = event.pattern_match.group(1)
 if event.sender_id == OWNER_ID:
     pass
 else:
    if not quew:
       await event.reply("Provide some text to draw! Example: /logo <your name>")
       return
    else:
       pass
 xnxx = await event.reply("Preparing Logo")
 try:
    text = event.pattern_match.group(1)
    ambilpoto = glob.glob("./resources/extras/*")
    peler = random.choice(ambilpoto)
    img = Image.open(peler)
    draw = ImageDraw.Draw(img)
    image_widthz, image_heightz = img.size
    ambilfont = glob.glob("./resources/fonts/*")
    rfont = random.choice(ambilfont)
    font = ImageFont.truetype(rfont, 150)
    w, h = draw.textsize(text, font=font)
    h += int(h*0.95)
    image_width, image_height = img.size
    draw.text(((image_widthz-w)/2, (image_heightz-h)/2), text, font=font, fill=(300, 300, 300))
    x = (image_widthz-w)/2.5
    y = ((image_heightz-h)/2+6)
     
    draw.text((x, y), text, font=font, fill="white", stroke_width=19, stroke_fill="black")
    fname2 = "LogoByIronman.png"
    img.save(fname2, "png")
    await xnxx.edit("Uploading")
    await tbot.send_file(event.chat_id, fname2, caption="Made By Ironman")
    if os.path.exists(fname2):
            os.remove(fname2)
            await xnxx.delete()
 except Exception as e:
   await event.reply(f"Error Report @Ironman_Support1, {e}")


file_help = os.path.basename(__file__)
file_help = file_help.replace(".py", "")
file_helpo = file_help.replace("_", "")
