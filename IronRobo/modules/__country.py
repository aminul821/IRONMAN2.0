import html

import flag
from countryinfo import CountryInfo
from IronRobo.events import register


def _join(value, sep=", "):
    if not value:
        return "-"
    if isinstance(value, dict):
        value = value.values()
    if isinstance(value, (list, tuple, set)) or hasattr(value, "__iter__") and not isinstance(value, str):
        return sep.join(str(v) for v in value)
    return str(value)


@register(pattern="^/country (.*)")
async def country_info(event):
    if event.fwd_from:
        return
    input_str = event.pattern_match.group(1).strip()
    try:
        a = CountryInfo(input_str).info()
    except Exception:
        a = None
    if not a:
        await event.reply("Country Not Available Currently")
        return

    iso = a.get("ISO") or {}
    try:
        country_flag = flag.flag(iso.get("alpha2", "").upper())
    except Exception:
        country_flag = "-"
    try:
        country_type = a["geoJSON"]["features"][0]["geometry"]["type"]
    except (KeyError, IndexError, TypeError):
        country_type = "-"
    population = a.get("population")
    if isinstance(population, int):
        population = f"{population:,}"

    rows = [
        ("Country Name", a.get("name")),
        ("Alternative Spellings", _join(a.get("altSpellings"))),
        ("Country Area", f"{a.get('area')} square kilometers" if a.get("area") else "-"),
        ("Borders", _join(a.get("borders"))),
        ("Calling Codes", _join(a.get("callingCodes"), " ")),
        ("Country's Capital", a.get("capital")),
        ("Country's currency", _join(a.get("currencies"))),
        ("Country's Flag", country_flag),
        ("Demonym", a.get("demonym")),
        ("Country Type", country_type),
        ("ISO Names", _join(iso)),
        ("Languages", _join(a.get("languages"))),
        ("Native Name", a.get("nativeName")),
        ("Population", population),
        ("Region", a.get("region")),
        ("Sub Region", a.get("subregion")),
        ("Time Zones", _join(a.get("timezones"))),
        ("Top Level Domain", _join(a.get("tld"))),
        ("Wikipedia", a.get("wiki")),
    ]
    caption = "<b><u>Information Gathered Successfully</u></b>\n\n" + "\n".join(
        f"<b>{name}:</b> {html.escape(str(value if value not in (None, '') else '-'))}"
        for name, value in rows
    )
    await event.reply(caption, parse_mode="html", link_preview=False)


__help__ = """
 • `/country <country name>`*:* Gathers information about a country
"""
__mod_name__ = "Country"
