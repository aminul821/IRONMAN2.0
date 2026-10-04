import datetime
import html
from typing import List

import pytz
from IronRobo import dispatcher
from IronRobo.modules.disable import DisableAbleCommandHandler
from telegram import ParseMode, Update
from telegram.ext import CallbackContext, run_async

# Built from the tz database that ships with pytz, so no API key is needed.
ZONES = []
for _code, _zones in pytz.country_timezones.items():
    for _zone in _zones:
        ZONES.append(
            {
                "countryCode": _code,
                "countryName": pytz.country_names.get(_code, _code),
                "zoneName": _zone,
            }
        )


def generate_time(to_find: str, findtype: List[str]) -> str:
    match = None
    for zone in ZONES:
        for eachtype in findtype:
            value = zone[eachtype].lower()
            if (eachtype == "countryCode" and value == to_find) or (
                eachtype != "countryCode" and to_find in value
            ):
                match = zone
                break
        if match:
            break
    if not match:
        return None

    tz = pytz.timezone(match["zoneName"])
    timestamp = datetime.datetime.now(tz)
    daylight_saving = "Yes" if timestamp.dst() else "No"
    offset = timestamp.strftime("%z")
    return (
        f"<b>Country:</b> <code>{html.escape(match['countryName'])}</code>\n"
        f"<b>Zone Name:</b> <code>{match['zoneName']}</code>\n"
        f"<b>Country Code:</b> <code>{match['countryCode']}</code>\n"
        f"<b>UTC Offset:</b> <code>{offset[:3]}:{offset[3:]}</code>\n"
        f"<b>Daylight saving:</b> <code>{daylight_saving}</code>\n"
        f"<b>Day:</b> <code>{timestamp.strftime('%A')}</code>\n"
        f"<b>Current Time:</b> <code>{timestamp.strftime('%H:%M:%S')}</code>\n"
        f"<b>Current Date:</b> <code>{timestamp.strftime('%d-%m-%Y')}</code>\n"
        '<b>Timezones:</b> <a href="https://en.wikipedia.org/wiki/List_of_tz_database_time_zones">List here</a>'
    )


@run_async
def gettime(update: Update, context: CallbackContext):
    message = update.effective_message

    try:
        query = message.text.strip().split(" ", 1)[1]
    except:
        message.reply_text("Provide a country name/abbreviation/timezone to find.")
        return
    send_message = message.reply_text(
        f"Finding timezone info for <b>{html.escape(query)}</b>", parse_mode=ParseMode.HTML
    )

    query_timezone = query.lower()
    if len(query_timezone) == 2:
        result = generate_time(query_timezone, ["countryCode"])
    else:
        result = generate_time(query_timezone, ["zoneName", "countryName"])

    if not result:
        send_message.edit_text(
            f"Timezone info not available for <b>{html.escape(query)}</b>\n"
            '<b>All Timezones:</b> <a href="https://en.wikipedia.org/wiki/List_of_tz_database_time_zones">List here</a>',
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    send_message.edit_text(
        result, parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


TIME_HANDLER = DisableAbleCommandHandler("time", gettime)

dispatcher.add_handler(TIME_HANDLER)

__mod_name__ = "TIME"
__command_list__ = ["time"]
__handlers__ = [TIME_HANDLER]
