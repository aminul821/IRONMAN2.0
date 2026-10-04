import threading

from IronRobo.modules.sql import BASE, SESSION, ensure_table
from sqlalchemy import BigInteger, Column, Integer, func


class Karma(BASE):
    __tablename__ = "karma"
    chat_id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, primary_key=True)
    karma = Column(Integer, default=0, nullable=False)

    def __init__(self, chat_id, user_id, karma=0):
        self.chat_id = chat_id
        self.user_id = user_id
        self.karma = karma


ensure_table(Karma.__table__)

KARMA_LOCK = threading.RLock()


def change_karma(chat_id: int, user_id: int, amount: int) -> int:
    """Add `amount` to a user's karma in a chat and return the new total."""
    with KARMA_LOCK:
        try:
            row = SESSION.query(Karma).get((chat_id, user_id))
            if not row:
                row = Karma(chat_id, user_id, 0)
            row.karma += amount
            SESSION.add(row)
            SESSION.commit()
            return row.karma
        finally:
            SESSION.close()


def get_karma(chat_id: int, user_id: int) -> int:
    try:
        row = SESSION.query(Karma).get((chat_id, user_id))
        return row.karma if row else 0
    finally:
        SESSION.close()


def top_karma(chat_id: int, limit: int = 10):
    try:
        return [
            (r.user_id, r.karma)
            for r in SESSION.query(Karma)
            .filter(Karma.chat_id == chat_id)
            .order_by(Karma.karma.desc())
            .limit(limit)
            .all()
        ]
    finally:
        SESSION.close()


def karma_stats():
    try:
        chats = SESSION.query(func.count(func.distinct(Karma.chat_id))).scalar()
        total = SESSION.query(func.coalesce(func.sum(Karma.karma), 0)).scalar()
        return chats, total
    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    with KARMA_LOCK:
        for row in SESSION.query(Karma).filter(Karma.chat_id == old_chat_id).all():
            row.chat_id = new_chat_id
        SESSION.commit()
