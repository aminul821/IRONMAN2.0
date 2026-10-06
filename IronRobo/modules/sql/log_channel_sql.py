import threading

from IronRobo.modules.sql import BASE, SESSION, ensure_table
from sqlalchemy import Column, String, distinct, func


class GroupLogs(BASE):
    __tablename__ = "log_channels"
    chat_id = Column(String(14), primary_key=True)
    log_channel = Column(String(14), nullable=False)

    def __init__(self, chat_id, log_channel):
        self.chat_id = str(chat_id)
        self.log_channel = str(log_channel)


ensure_table(GroupLogs.__table__)

LOGS_INSERTION_LOCK = threading.RLock()

CHANNELS = {}


def set_chat_log_channel(chat_id, log_channel):
    with LOGS_INSERTION_LOCK:
        res = SESSION.query(GroupLogs).get(str(chat_id))
        if res:
            res.log_channel = log_channel
        else:
            res = GroupLogs(chat_id, log_channel)
            SESSION.add(res)

        CHANNELS[str(chat_id)] = log_channel
        SESSION.commit()


def get_chat_log_channel(chat_id):
    return CHANNELS.get(str(chat_id))


def stop_chat_logging(chat_id):
    with LOGS_INSERTION_LOCK:
        res = SESSION.query(GroupLogs).get(str(chat_id))
        if res:
            if str(chat_id) in CHANNELS:
                del CHANNELS[str(chat_id)]

            log_channel = res.log_channel
            SESSION.delete(res)
            SESSION.commit()
            return log_channel


def num_logchannels():
    try:
        return SESSION.query(func.count(distinct(GroupLogs.chat_id))).scalar()
    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    with LOGS_INSERTION_LOCK:
        chat = SESSION.query(GroupLogs).get(str(old_chat_id))
        if chat:
            chat.chat_id = str(new_chat_id)
            SESSION.add(chat)
            if str(old_chat_id) in CHANNELS:
                CHANNELS[str(new_chat_id)] = CHANNELS.get(str(old_chat_id))

        SESSION.commit()


def __load_log_channels():
    global CHANNELS
    try:
        all_chats = SESSION.query(GroupLogs).all()
        CHANNELS = {chat.chat_id: chat.log_channel for chat in all_chats}
    finally:
        SESSION.close()


__load_log_channels()


class LogSettings(BASE):
    """Log categories a chat turned off (comma separated)."""

    __tablename__ = "log_settings"
    chat_id = Column(String(20), primary_key=True)
    disabled = Column(String(200), nullable=False, default="")

    def __init__(self, chat_id, disabled=""):
        self.chat_id = str(chat_id)
        self.disabled = disabled


ensure_table(LogSettings.__table__)

DISABLED_CATEGORIES = {}


def get_disabled_categories(chat_id):
    return DISABLED_CATEGORIES.get(str(chat_id), set())


def set_disabled_categories(chat_id, categories):
    categories = set(categories)
    with LOGS_INSERTION_LOCK:
        try:
            row = SESSION.query(LogSettings).get(str(chat_id))
            if not row:
                row = LogSettings(chat_id)
                SESSION.add(row)
            row.disabled = ",".join(sorted(categories))
            SESSION.commit()
        finally:
            SESSION.close()
        DISABLED_CATEGORIES[str(chat_id)] = categories


def __load_log_settings():
    try:
        for row in SESSION.query(LogSettings).all():
            DISABLED_CATEGORIES[row.chat_id] = {c for c in row.disabled.split(",") if c}
    finally:
        SESSION.close()


__load_log_settings()


class JoinLinks(BASE):
    """Which invite link a member joined with, shown again when they leave."""

    __tablename__ = "log_join_links"
    chat_id = Column(String(20), primary_key=True)
    user_id = Column(String(20), primary_key=True)
    link = Column(String(200), nullable=False, default="")
    name = Column(String(100), nullable=False, default="")
    creator_id = Column(String(20), nullable=False, default="")
    creator_name = Column(String(100), nullable=False, default="")

    def __init__(self, chat_id, user_id):
        self.chat_id = str(chat_id)
        self.user_id = str(user_id)


ensure_table(JoinLinks.__table__)


def set_join_link(chat_id, user_id, link, name, creator_id, creator_name):
    with LOGS_INSERTION_LOCK:
        try:
            row = SESSION.query(JoinLinks).get((str(chat_id), str(user_id)))
            if not row:
                row = JoinLinks(chat_id, user_id)
                SESSION.add(row)
            row.link = (link or "")[:200]
            row.name = (name or "")[:100]
            row.creator_id = str(creator_id or "")
            row.creator_name = (creator_name or "")[:100]
            SESSION.commit()
        finally:
            SESSION.close()


def pop_join_link(chat_id, user_id):
    """The saved link as (link, name, creator_id, creator_name), or None. Removes it."""
    with LOGS_INSERTION_LOCK:
        try:
            row = SESSION.query(JoinLinks).get((str(chat_id), str(user_id)))
            if not row:
                return None
            data = (row.link, row.name, row.creator_id, row.creator_name)
            SESSION.delete(row)
            SESSION.commit()
            return data
        finally:
            SESSION.close()
