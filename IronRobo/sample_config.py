# Create a new config.py or rename this to config.py file in same dir and import, then extend this class.
# (Only needed when you don't use environment variables, i.e. when ENV is not set.)
import json
import os


def get_user_list(config, key):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config)
    if not os.path.exists(path):
        return []
    with open(path, "r") as json_file:
        return json.load(json_file).get(key, [])


class Config(object):
    LOGGER = True
    # REQUIRED
    # Login to https://my.telegram.org and fill in these slots with the details given by it

    API_ID = 123456  # integer value, dont use ""
    API_HASH = "awoo"
    TOKEN = "BOT_TOKEN"  # Get it from @BotFather
    OWNER_ID = 792109647  # Your own user id, an integer
    OWNER_USERNAME = "Sawada"
    SUPPORT_CHAT = None  # Your own group for support, without the @
    JOIN_LOGGER = None  # Chat id where the bot logs the groups it's added to
    EVENT_LOGS = None  # Chat id where the bot logs gbans, sudo promotes, errors...

    # PostgreSQL database, eg "postgresql://user:password@host:5432/database"
    SQLALCHEMY_DATABASE_URI = "postgresql://user:password@localhost:5432/ironman"
    MONGO_DB_URI = None  # not needed anymore
    REDIS_URL = None  # not needed anymore

    # RECOMMENDED
    LOAD = []
    NO_LOAD = []
    WEBHOOK = False
    INFOPIC = True
    URL = None
    SPAMWATCH_API = ""  # go to support.spamwat.ch to get key
    SPAMWATCH_SUPPORT_CHAT = "@SpamWatchSupport"

    # OPTIONAL
    ##List of id's -  (not usernames) for users which have sudo access to the bot.
    DRAGONS = get_user_list("elevated_users.json", "sudos")
    ##List of id's - (not usernames) for developers who will have the same perms as the owner
    DEV_USERS = get_user_list("elevated_users.json", "devs")
    ##List of id's (not usernames) for users which are allowed to gban, but can also be banned.
    DEMONS = get_user_list("elevated_users.json", "supports")
    # List of id's (not usernames) for users which WONT be banned/kicked by the bot.
    TIGERS = get_user_list("elevated_users.json", "tigers")
    WOLVES = get_user_list("elevated_users.json", "whitelists")
    DONATION_LINK = None  # EG, paypal
    CERT_PATH = None
    PORT = 5000
    BOT_ID = None  # worked out from TOKEN when empty
    DEL_CMDS = True  # Delete commands that users dont have access to, like delete /ban if a non admin uses it.
    STRICT_GBAN = True
    STRICT_GMUTE = False
    WORKERS = 8  # Number of subthreads to use. Set as number of threads your processor uses
    BAN_STICKER = ""  # banhammer marie sticker id, the bot will send this sticker before banning or kicking a user in chat.
    ALLOW_EXCL = True  # Allow ! commands as well as / (Leave this to true so that blacklist can work)
    TEMP_DOWNLOAD_DIRECTORY = "./"
    HEROKU_API_KEY = None
    HEROKU_APP_NAME = None
    VIRUS_API_KEY = None
    OPENWEATHERMAP_ID = None  # optional, https://openweathermap.org/api (wttr.in is used otherwise)
    CASH_API_KEY = None  # optional, https://www.alphavantage.co/support/#api-key (free rates are used otherwise)
    TIME_API_KEY = None  # not needed anymore
    WALL_API = None  # not needed anymore
    AI_API_KEY = None  # Anthropic API key for the chatbot, https://console.anthropic.com
    AI_MODEL = "claude-opus-5-5"
    GENIUS_API_TOKEN = None  # optional, for better /lyrics results
    BL_CHATS = []  # List of groups that you want blacklisted.
    # Group ids the bot works in. Groups the owner adds the bot to are allowed
    # automatically; from any other group the bot leaves. Empty = no restriction.
    ALLOWED_GROUPS = []
    ALLOW_CHATS = True
    SPAMMERS = None


class Production(Config):
    LOGGER = True


class Development(Config):
    LOGGER = True
