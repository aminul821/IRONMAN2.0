"""Upload a media file to a public file host and return its URL.

telegra.ph stopped accepting media uploads, so catbox.moe (keyless) is used
instead, with 0x0.st as a fallback.
"""
import os

import requests

TIMEOUT = 60


def _catbox(path):
    with open(path, "rb") as f:
        r = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (os.path.basename(path), f)},
            timeout=TIMEOUT,
        )
    if r.ok and r.text.startswith("http"):
        return r.text.strip()
    return None


def _0x0(path):
    with open(path, "rb") as f:
        r = requests.post(
            "https://0x0.st",
            files={"file": (os.path.basename(path), f)},
            headers={"User-Agent": "IronRobo/2.0"},
            timeout=TIMEOUT,
        )
    if r.ok and r.text.startswith("http"):
        return r.text.strip()
    return None


def upload_media(path):
    """Return a public URL for the file, or None if every host failed."""
    for host in (_catbox, _0x0):
        try:
            url = host(path)
        except requests.RequestException:
            url = None
        if url:
            return url
    return None
