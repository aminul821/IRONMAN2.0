import asyncio

from geopy.geocoders import Nominatim
from IronRobo import telethn as tbot
from IronRobo.events import register
from telethon.tl import types

geolocator = Nominatim(user_agent="IronRobo-telegram-bot")


@register(pattern="^/gps (.*)")
async def gps(event):
    location = event.pattern_match.group(1)
    try:
        geoloc = await asyncio.get_running_loop().run_in_executor(
            None, lambda: geolocator.geocode(location, timeout=15)
        )
    except Exception:
        geoloc = None
    if not geoloc:
        await event.reply("I can't find that")
        return
    latitude, longitude = geoloc.latitude, geoloc.longitude
    gm = "https://www.google.com/maps/search/{},{}".format(latitude, longitude)
    await tbot.send_file(
        event.chat_id,
        file=types.InputMediaGeoPoint(
            types.InputGeoPoint(float(latitude), float(longitude))
        ),
    )
    await event.reply(
        "{}\nOpen with: [🌏Google Maps]({})".format(geoloc.address, gm),
        link_preview=False,
    )


__help__ = """
 • `/gps <place>`*:* Sends the location of a place on the map
"""
__mod_name__ = "GPS"
