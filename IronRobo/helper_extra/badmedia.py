"""Local NSFW image detection.

The hosted API used before (starkapi.herokuapp.com) no longer exists, so the
check now runs locally with NudeNet (a small ONNX model bundled with the package).
"""
import asyncio
import os
import tempfile
import threading

from IronRobo import LOGGER

NSFW_CLASSES = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "ANUS_EXPOSED",
    "BUTTOCKS_EXPOSED",
}
MIN_SCORE = 0.5

_detector = None
_detector_lock = threading.Lock()


def _get_detector():
    global _detector
    with _detector_lock:
        if _detector is None:
            from nudenet import NudeDetector

            _detector = NudeDetector()
        return _detector


def _check_file(path):
    try:
        detections = _get_detector().detect(path)
    except Exception as e:
        LOGGER.warning("NSFW check failed for %s: %s", path, e)
        return False
    return any(
        d.get("class") in NSFW_CLASSES and d.get("score", 0) >= MIN_SCORE
        for d in detections
    )


async def is_nsfw(event):
    """Return True if the media in a telethon message looks like NSFW content."""
    msg = event
    if not (msg.gif or msg.video or msg.video_note or msg.photo or msg.sticker):
        return False
    if msg.sticker and msg.file and msg.file.mime_type == "application/x-tgsticker":
        # animated (lottie) stickers can't be checked as images
        return False

    tmpdir = tempfile.mkdtemp(prefix="nsfw_")
    path = None
    try:
        if msg.photo:
            path = await event.client.download_media(msg.media, tmpdir)
        else:
            # videos / gifs / stickers: check the thumbnail
            try:
                path = await event.client.download_media(msg.media, tmpdir, thumb=-1)
            except Exception:
                path = None
            if not path and msg.sticker:
                path = await event.client.download_media(msg.media, tmpdir)
        if not path or not os.path.exists(path):
            return False
        return await asyncio.get_running_loop().run_in_executor(None, _check_file, path)
    except Exception as e:
        LOGGER.warning("Could not download media for the NSFW check: %s", e)
        return False
    finally:
        for f in os.listdir(tmpdir):
            try:
                os.remove(os.path.join(tmpdir, f))
            except OSError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass
