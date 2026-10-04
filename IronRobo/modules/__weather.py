import io
import time
from urllib.parse import quote

import aiohttp
from IronRobo import OPENWEATHERMAP_ID
from IronRobo.events import register

TIMEOUT = aiohttp.ClientTimeout(total=20)


async def _openweathermap(city):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "APPID": OPENWEATHERMAP_ID, "units": "metric"}
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
    if str(data.get("cod")) != "200":
        return data.get("message", "City not found.")
    country_code = data["sys"]["country"]
    tz = int(data["timezone"])
    sunrise = time.strftime("%H:%M:%S", time.gmtime(int(data["sys"]["sunrise"]) + tz))
    sunset = time.strftime("%H:%M:%S", time.gmtime(int(data["sys"]["sunset"]) + tz))
    return (
        f"**Location**: {data['name']}, {country_code}\n"
        f"**Weather**: {data['weather'][0]['description'].title()}\n"
        f"**Temperature**: {data['main']['temp']}°С\n"
        f"    __minimum__: {data['main']['temp_min']}°С\n"
        f"    __maximum__: {data['main']['temp_max']}°С\n"
        f"**Humidity**: {data['main']['humidity']}%\n"
        f"**Wind**: {data['wind']['speed']}m/s\n"
        f"**Clouds**: {data['clouds']['all']}%\n"
        f"**Sunrise**: {sunrise}\n"
        f"**Sunset**: {sunset}"
    )


async def _wttr(city):
    url = f"https://wttr.in/{quote(city)}?format=j1"
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.get(url, headers={"User-Agent": "curl/8"}) as resp:
            if resp.status != 200:
                return "City not found."
            data = await resp.json(content_type=None)
    cur = data["current_condition"][0]
    area = data.get("nearest_area", [{}])[0]
    place = ", ".join(
        x[0]["value"] for x in (area.get("areaName"), area.get("country")) if x
    ) or city
    astro = data["weather"][0]["astronomy"][0]
    return (
        f"**Location**: {place}\n"
        f"**Weather**: {cur['weatherDesc'][0]['value']}\n"
        f"**Temperature**: {cur['temp_C']}°С (feels like {cur['FeelsLikeC']}°С)\n"
        f"    __minimum__: {data['weather'][0]['mintempC']}°С\n"
        f"    __maximum__: {data['weather'][0]['maxtempC']}°С\n"
        f"**Humidity**: {cur['humidity']}%\n"
        f"**Wind**: {cur['windspeedKmph']}km/h\n"
        f"**Clouds**: {cur['cloudcover']}%\n"
        f"**Sunrise**: {astro['sunrise']}\n"
        f"**Sunset**: {astro['sunset']}"
    )


@register(pattern="^/weather (.*)")
async def weather(event):
    if event.fwd_from:
        return
    city = event.pattern_match.group(1).strip()
    try:
        if OPENWEATHERMAP_ID:
            text = await _openweathermap(city)
        else:
            text = await _wttr(city)
    except Exception:
        text = "The weather service isn't reachable right now, try again later."
    await event.reply(text)


@register(pattern="^/wttr (.*)")
async def wttr(event):
    if event.fwd_from:
        return
    city = event.pattern_match.group(1).strip()
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(f"https://wttr.in/{quote(city)}.png") as resp:
                if resp.status != 200:
                    await event.reply("City not found.")
                    return
                data = await resp.read()
    except Exception:
        await event.reply("wttr.in isn't reachable right now, try again later.")
        return
    out_file = io.BytesIO(data)
    out_file.name = "weather.png"
    await event.reply(file=out_file)


__help__ = """
 • `/weather <city>`*:* Current weather of a city
 • `/wttr <city>`*:* Weather forecast as an image
"""
__mod_name__ = "Weather"
