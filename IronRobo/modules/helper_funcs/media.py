import inspect


def safe_sender(func):
    """Wrap a Bot.send_* method so it ignores keyword arguments it doesn't take.

    Filters, notes and welcomes call every send method with the same
    arguments (caption, parse_mode, disable_web_page_preview...), but e.g.
    send_sticker takes no caption and send_photo has no
    disable_web_page_preview, which made those calls raise TypeError.
    """
    accepted = set(inspect.signature(func).parameters)

    def send(*args, **kwargs):
        return func(*args, **{k: v for k, v in kwargs.items() if k in accepted})

    send.__wrapped__ = func
    return send
