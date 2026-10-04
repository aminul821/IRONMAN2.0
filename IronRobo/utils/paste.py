"""Upload text to a public paste service.

nekobin.com (used originally) is gone, so try a couple of keyless services.
"""
import requests

TIMEOUT = 15


def _paste_rs(text: str):
    r = requests.post("https://paste.rs/", data=text.encode("utf-8"), timeout=TIMEOUT)
    if r.status_code in (200, 201, 206):
        return r.text.strip()
    return None


def _dpaste(text: str):
    r = requests.post(
        "https://dpaste.org/api/",
        data={"content": text, "format": "url", "expires": "604800"},
        timeout=TIMEOUT,
    )
    if r.ok:
        return r.text.strip()
    return None


def paste_text(text: str):
    """Return the URL of the paste, or None if every service failed."""
    for service in (_paste_rs, _dpaste):
        try:
            url = service(text)
        except requests.RequestException:
            url = None
        if url and url.startswith("http"):
            return url
    return None
