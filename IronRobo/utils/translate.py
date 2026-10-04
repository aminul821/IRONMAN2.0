"""Google Translate with a fallback host.

The free endpoint rate limits busy servers (HTTP 429); the same API is also
served from translate.googleapis.com, which is limited separately.
"""
from gpytranslate import Translator

TRANSLATORS = [
    Translator(),
    Translator(url="https://translate.googleapis.com/translate_a/single"),
]


class TranslateUnavailable(Exception):
    pass


async def translate(text, source="auto", dest="en"):
    """Return the gpytranslate result (.text and .lang) or raise TranslateUnavailable."""
    last_error = None
    for translator in TRANSLATORS:
        try:
            return await translator(text, sourcelang=source, targetlang=dest)
        except Exception as e:  # gpytranslate wraps HTTP/JSON errors
            last_error = e
    raise TranslateUnavailable(str(last_error))


async def detect(text):
    return (await translate(text)).lang
