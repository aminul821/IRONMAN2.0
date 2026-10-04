import json
import logging
import os
import sys
import time

import warnings

# APScheduler 3.6 (used by python-telegram-bot 13) imports pkg_resources,
# which warns on every start; setuptools is pinned so it keeps working.
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

import spamwatch
import telegram.ext as tg
from telegram.utils.deprecate import TelegramDeprecationWarning

# python-telegram-bot 13 warns about every old-style handler on each update,
# which floods the logs without anything to act on.
warnings.filterwarnings("ignore", category=TelegramDeprecationWarning)
from pyrogram import Client, errors
from telethon import TelegramClient

StartTime = time.time()

# enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("telethon").setLevel(logging.WARNING)

LOGGER = logging.getLogger(__name__)

# if version < 3.9, stop bot.
if sys.version_info < (3, 9):
    LOGGER.error(
        "You MUST have a python version of at least 3.9! Multiple features depend on this. Bot quitting."
    )
    quit(1)


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() not in ("0", "false", "no", "off", "none")


def _env_int(name, default=None):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value.strip())
    except ValueError:
        raise Exception(f"Your {name} env variable is not a valid integer.")


def _env_id_set(name):
    try:
        return set(int(x) for x in os.environ.get(name, "").replace(",", " ").split())
    except ValueError:
        raise Exception(f"Your {name} list does not contain valid integers.")


ENV = _env_bool("ENV", False)

if ENV:
    TOKEN = os.environ.get("TOKEN", None)
    OWNER_ID = _env_int("OWNER_ID")
    JOIN_LOGGER = _env_int("JOIN_LOGGER")
    OWNER_USERNAME = os.environ.get("OWNER_USERNAME", None)

    DRAGONS = _env_id_set("DRAGONS")
    DEV_USERS = _env_id_set("DEV_USERS")
    DEMONS = _env_id_set("DEMONS")
    WOLVES = _env_id_set("WOLVES")
    TIGERS = _env_id_set("TIGERS")

    INFOPIC = _env_bool("INFOPIC", True)
    EVENT_LOGS = _env_int("EVENT_LOGS")
    WEBHOOK = _env_bool("WEBHOOK", False)
    URL = os.environ.get("URL", "")  # Does not contain token
    PORT = _env_int("PORT", 5000)
    CERT_PATH = os.environ.get("CERT_PATH")
    API_ID = _env_int("API_ID")
    API_HASH = os.environ.get("API_HASH", None)
    DB_URI = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    MONGO_DB_URI = os.environ.get("MONGO_DB_URI", None)
    REDIS_URL = os.environ.get("REDIS_URL", None)
    DONATION_LINK = os.environ.get("DONATION_LINK")
    HEROKU_API_KEY = os.environ.get("HEROKU_API_KEY", None)
    HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME", None)
    TEMP_DOWNLOAD_DIRECTORY = os.environ.get("TEMP_DOWNLOAD_DIRECTORY", "./")
    OPENWEATHERMAP_ID = os.environ.get("OPENWEATHERMAP_ID") or os.environ.get(
        "API_OPENWEATHER"
    )
    VIRUS_API_KEY = os.environ.get("VIRUS_API_KEY", None)
    LOAD = os.environ.get("LOAD", "").split()
    BOT_ID = _env_int("BOT_ID")
    NO_LOAD = os.environ.get("NO_LOAD", "").split()
    DEL_CMDS = _env_bool("DEL_CMDS", False)
    STRICT_GBAN = _env_bool("STRICT_GBAN", True)
    WORKERS = _env_int("WORKERS", 8)
    BAN_STICKER = os.environ.get("BAN_STICKER", "")
    ALLOW_EXCL = _env_bool("ALLOW_EXCL", True)
    CASH_API_KEY = os.environ.get("CASH_API_KEY", None)
    TIME_API_KEY = os.environ.get("TIME_API_KEY", None)
    AI_API_KEY = os.environ.get("AI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    AI_MODEL = os.environ.get("AI_MODEL", "claude-opus-5-5")
    WALL_API = os.environ.get("WALL_API", None)
    SUPPORT_CHAT = os.environ.get("SUPPORT_CHAT", None)
    SPAMWATCH_SUPPORT_CHAT = os.environ.get("SPAMWATCH_SUPPORT_CHAT", None)
    SPAMWATCH_API = os.environ.get("SPAMWATCH_API") or os.environ.get("sw_api")
    STRICT_GMUTE = _env_bool("STRICT_GMUTE", False)
    GENIUS_API_TOKEN = os.environ.get("GENIUS_API_TOKEN", None)
    ALLOW_CHATS = _env_bool("ALLOW_CHATS", True)
    BL_CHATS = _env_id_set("BL_CHATS")

else:
    from IronRobo.config import Development as Config

    TOKEN = Config.TOKEN

    try:
        OWNER_ID = int(Config.OWNER_ID)
    except ValueError:
        raise Exception("Your OWNER_ID variable is not a valid integer.")

    JOIN_LOGGER = Config.JOIN_LOGGER
    OWNER_USERNAME = Config.OWNER_USERNAME
    ALLOW_CHATS = getattr(Config, "ALLOW_CHATS", True)
    try:
        DRAGONS = set(int(x) for x in Config.DRAGONS or [])
        DEV_USERS = set(int(x) for x in Config.DEV_USERS or [])
    except ValueError:
        raise Exception("Your sudo or dev users list does not contain valid integers.")

    try:
        DEMONS = set(int(x) for x in Config.DEMONS or [])
    except ValueError:
        raise Exception("Your support users list does not contain valid integers.")

    try:
        WOLVES = set(int(x) for x in Config.WOLVES or [])
    except ValueError:
        raise Exception("Your whitelisted users list does not contain valid integers.")

    try:
        TIGERS = set(int(x) for x in Config.TIGERS or [])
    except ValueError:
        raise Exception("Your tiger users list does not contain valid integers.")

    EVENT_LOGS = Config.EVENT_LOGS
    WEBHOOK = Config.WEBHOOK
    URL = Config.URL
    PORT = Config.PORT
    CERT_PATH = Config.CERT_PATH
    API_ID = Config.API_ID
    API_HASH = Config.API_HASH

    DB_URI = Config.SQLALCHEMY_DATABASE_URI
    MONGO_DB_URI = Config.MONGO_DB_URI
    HEROKU_API_KEY = Config.HEROKU_API_KEY
    HEROKU_APP_NAME = Config.HEROKU_APP_NAME
    TEMP_DOWNLOAD_DIRECTORY = Config.TEMP_DOWNLOAD_DIRECTORY
    OPENWEATHERMAP_ID = Config.OPENWEATHERMAP_ID
    VIRUS_API_KEY = Config.VIRUS_API_KEY
    DONATION_LINK = Config.DONATION_LINK
    LOAD = Config.LOAD
    BOT_ID = Config.BOT_ID
    NO_LOAD = Config.NO_LOAD
    DEL_CMDS = Config.DEL_CMDS
    STRICT_GBAN = Config.STRICT_GBAN
    WORKERS = Config.WORKERS
    BAN_STICKER = Config.BAN_STICKER
    ALLOW_EXCL = Config.ALLOW_EXCL
    CASH_API_KEY = Config.CASH_API_KEY
    TIME_API_KEY = Config.TIME_API_KEY
    AI_API_KEY = Config.AI_API_KEY
    AI_MODEL = getattr(Config, "AI_MODEL", "claude-opus-5-5")
    WALL_API = Config.WALL_API
    SUPPORT_CHAT = Config.SUPPORT_CHAT
    SPAMWATCH_SUPPORT_CHAT = Config.SPAMWATCH_SUPPORT_CHAT
    SPAMWATCH_API = Config.SPAMWATCH_API
    INFOPIC = Config.INFOPIC
    STRICT_GMUTE = Config.STRICT_GMUTE
    REDIS_URL = Config.REDIS_URL
    GENIUS_API_TOKEN = getattr(Config, "GENIUS_API_TOKEN", None)

    try:
        BL_CHATS = set(int(x) for x in Config.BL_CHATS or [])
    except ValueError:
        raise Exception("Your blacklisted chats list does not contain valid integers.")

if not TOKEN:
    raise Exception("TOKEN is missing! Get one from @BotFather and set it.")
if OWNER_ID is None:
    raise Exception("OWNER_ID is missing! Set it to your own Telegram user id.")
if not API_ID or not API_HASH:
    raise Exception("API_ID / API_HASH are missing! Get them from my.telegram.org.")

# The numeric part of the bot token is the bot's user id.
if not BOT_ID:
    BOT_ID = int(TOKEN.split(":")[0])
BOT_ID = int(BOT_ID)

if not DB_URI:
    raise Exception("DATABASE_URL is missing! A PostgreSQL database is required.")
# Heroku/Render style URIs use "postgres://", which SQLAlchemy no longer accepts.
if DB_URI.startswith("postgres://"):
    DB_URI = DB_URI.replace("postgres://", "postgresql://", 1)

if not SUPPORT_CHAT:
    SUPPORT_CHAT = None
elif SUPPORT_CHAT.startswith("@"):
    SUPPORT_CHAT = SUPPORT_CHAT[1:]

# Users promoted with /addsudo, /addsupport... are saved in elevated_users.json;
# load them on top of the ones from the environment.
_ELEVATED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elevated_users.json")
if ENV and os.path.exists(_ELEVATED_FILE):
    try:
        with open(_ELEVATED_FILE) as _f:
            _elevated = json.load(_f)
        DRAGONS.update(int(x) for x in _elevated.get("sudos", []))
        DEV_USERS.update(int(x) for x in _elevated.get("devs", []))
        DEMONS.update(int(x) for x in _elevated.get("supports", []))
        WOLVES.update(int(x) for x in _elevated.get("whitelists", []))
        TIGERS.update(int(x) for x in _elevated.get("tigers", []))
    except (ValueError, OSError) as e:
        LOGGER.warning("Could not read elevated_users.json: %s", e)

DRAGONS.add(OWNER_ID)
DEV_USERS.add(OWNER_ID)

if not SPAMWATCH_API:
    sw = None
    LOGGER.warning("SpamWatch API key missing! recheck your config.")
else:
    try:
        sw = spamwatch.Client(SPAMWATCH_API)
    except Exception:
        sw = None
        LOGGER.warning("Can't connect to SpamWatch!")

# Pyrogram 1.x rejects the ids of supergroups/channels created after 2021
# ("Peer id invalid"); widen its accepted id range.
import pyrogram.utils as _pyro_utils

_pyro_utils.MIN_CHANNEL_ID = -1009999999999
_pyro_utils.MIN_CHAT_ID = -999999999999

# Pyrogram 1.4 can't connect when its message id clock is off; see the module.
from IronRobo.utils import pyrogram_fix as _pyrogram_fix

_pyrogram_fix.apply()

updater = tg.Updater(TOKEN, workers=WORKERS, use_context=True)
telethn = TelegramClient("ironman", API_ID, API_HASH)
pbot = Client("ironmanpbot", api_id=API_ID, api_hash=API_HASH, bot_token=TOKEN)
dispatcher = updater.dispatcher

DRAGONS = list(DRAGONS) + list(DEV_USERS)
DEV_USERS = list(DEV_USERS)
WOLVES = list(WOLVES)
DEMONS = list(DEMONS)
TIGERS = list(TIGERS)

# Load at end to ensure all prev variables have been set
from IronRobo.modules.helper_funcs.handlers import (
    CustomCommandHandler,
    CustomMessageHandler,
    CustomRegexHandler,
)

# make sure the regex handler can take extra kwargs
tg.RegexHandler = CustomRegexHandler
tg.CommandHandler = CustomCommandHandler
tg.MessageHandler = CustomMessageHandler
