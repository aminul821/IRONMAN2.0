import threading

from IronRobo.modules.sql import BASE, SESSION, ensure_table
from sqlalchemy import Column, String


class AllowedChat(BASE):
    """Groups the owner added the bot to (on top of ALLOWED_GROUPS)."""

    __tablename__ = "allowed_chats"
    chat_id = Column(String(20), primary_key=True)

    def __init__(self, chat_id):
        self.chat_id = str(chat_id)


ensure_table(AllowedChat.__table__)

LOCK = threading.RLock()
ALLOWED = set()


def is_allowed(chat_id) -> bool:
    return str(chat_id) in ALLOWED


def allow(chat_id):
    with LOCK:
        try:
            SESSION.merge(AllowedChat(chat_id))
            SESSION.commit()
        finally:
            SESSION.close()
        ALLOWED.add(str(chat_id))


def disallow(chat_id) -> bool:
    with LOCK:
        try:
            row = SESSION.query(AllowedChat).get(str(chat_id))
            if row:
                SESSION.delete(row)
                SESSION.commit()
        finally:
            SESSION.close()
        existed = str(chat_id) in ALLOWED
        ALLOWED.discard(str(chat_id))
        return existed


def all_allowed():
    return sorted(ALLOWED)


def migrate_chat(old_chat_id, new_chat_id):
    if is_allowed(old_chat_id):
        disallow(old_chat_id)
        allow(new_chat_id)


def __load():
    try:
        ALLOWED.update(row.chat_id for row in SESSION.query(AllowedChat).all())
    finally:
        SESSION.close()


__load()
