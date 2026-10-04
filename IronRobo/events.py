import importlib
import logging
import sys

from telethon import events
from IronRobo import telethn


def register(**args):
    """ Registers a new message. """
    pattern = args.get("pattern", None)

    r_pattern = r"^[/!]"

    if pattern is not None:
        pattern = pattern.replace("^/", r_pattern, 1)
        if not pattern.startswith("(?i)"):
            pattern = "(?i)" + pattern
        args["pattern"] = pattern

    def decorator(func):
        telethn.add_event_handler(func, events.NewMessage(**args))
        return func

    return decorator


def chataction(**args):
    """ Registers chat actions. """

    def decorator(func):
        telethn.add_event_handler(func, events.ChatAction(**args))
        return func

    return decorator


def userupdate(**args):
    """ Registers user updates. """

    def decorator(func):
        telethn.add_event_handler(func, events.UserUpdate(**args))
        return func

    return decorator


def inlinequery(**args):
    """ Registers inline query. """
    pattern = args.get("pattern", None)

    if pattern is not None and not pattern.startswith("(?i)"):
        args["pattern"] = "(?i)" + pattern

    def decorator(func):
        telethn.add_event_handler(func, events.InlineQuery(**args))
        return func

    return decorator


def callbackquery(**args):
    """ Registers inline query. """

    def decorator(func):
        telethn.add_event_handler(func, events.CallbackQuery(**args))
        return func

    return decorator


def load_module(shortname):
    """Import (or re-import) a module from IronRobo/modules at runtime."""
    name = "IronRobo.modules.{}".format(shortname)
    if name in sys.modules:
        return importlib.reload(sys.modules[name])
    mod = importlib.import_module(name)
    logging.getLogger(__name__).info("Successfully imported %s", shortname)
    return mod
