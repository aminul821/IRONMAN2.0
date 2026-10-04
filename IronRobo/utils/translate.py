"""Google Translate with a fallback host and a cool-down.

The free endpoint rate limits busy servers (HTTP 429); the same API is also
served from translate.googleapis.com, which is limited separately. When both
refuse, stop asking for a while: retrying on every message only keeps the
server blocked.
"""
import time

from gpytranslate import Translator

TRANSLATORS = [
    Translator(),
    Translator(url="https://translate.googleapis.com/translate_a/single"),
]
COOLDOWN = 10 * 60  # seconds to wait after Google refused every host
_blocked_until = 0.0


class TranslateUnavailable(Exception):
    pass


async def translate(text, source="auto", dest="en"):
    """Return the gpytranslate result (.text and .lang) or raise TranslateUnavailable."""
    global _blocked_until
    if time.monotonic() < _blocked_until:
        raise TranslateUnavailable("rate limited, cooling down")
    last_error = None
    for translator in TRANSLATORS:
        try:
            return await translator(text, sourcelang=source, targetlang=dest)
        except Exception as e:  # gpytranslate wraps HTTP/JSON errors
            last_error = e
    _blocked_until = time.monotonic() + COOLDOWN
    raise TranslateUnavailable(str(last_error))


async def detect(text):
    return (await translate(text)).lang
