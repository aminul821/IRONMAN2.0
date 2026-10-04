import threading

from IronRobo.modules.sql import BASE, SESSION, ensure_table
from sqlalchemy import Column, String


class ProfanityChats(BASE):
    __tablename__ = "profanity_chats"
    chat_id = Column(String(14), primary_key=True)

    def __init__(self, chat_id):
        self.chat_id = str(chat_id)


class EnglishOnlyChats(BASE):
    __tablename__ = "english_only_chats"
    chat_id = Column(String(14), primary_key=True)

    def __init__(self, chat_id):
        self.chat_id = str(chat_id)


ensure_table(ProfanityChats.__table__)
ensure_table(EnglishOnlyChats.__table__)

LOCK = threading.RLock()
PROFANITY = set()
ENGLISH_ONLY = set()


def _set(model, cache, chat_id, enabled):
    chat_id = str(chat_id)
    with LOCK:
        try:
            row = SESSION.query(model).get(chat_id)
            if enabled and not row:
                SESSION.add(model(chat_id))
            elif not enabled and row:
                SESSION.delete(row)
            SESSION.commit()
        finally:
            SESSION.close()
        if enabled:
            cache.add(chat_id)
        else:
            cache.discard(chat_id)


def set_profanity(chat_id, enabled: bool):
    _set(ProfanityChats, PROFANITY, chat_id, enabled)


def is_profanity(chat_id) -> bool:
    return str(chat_id) in PROFANITY


def set_english_only(chat_id, enabled: bool):
    _set(EnglishOnlyChats, ENGLISH_ONLY, chat_id, enabled)


def is_english_only(chat_id) -> bool:
    return str(chat_id) in ENGLISH_ONLY


def __load_cache():
    try:
        PROFANITY.update(r.chat_id for r in SESSION.query(ProfanityChats).all())
        ENGLISH_ONLY.update(r.chat_id for r in SESSION.query(EnglishOnlyChats).all())
    finally:
        SESSION.close()


__load_cache()
