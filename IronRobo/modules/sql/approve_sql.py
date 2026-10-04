import threading

from sqlalchemy import BigInteger, Column, String, UnicodeText, Integer, func, distinct

from IronRobo.modules.sql import BASE, SESSION, ensure_table


class Approvals(BASE):
    __tablename__ = "approval"
    chat_id = Column(String(14), primary_key=True)
    user_id = Column(BigInteger, primary_key=True)

    def __init__(self, chat_id, user_id):
        self.chat_id = str(chat_id)  # ensure string
        self.user_id = user_id

    def __repr__(self):
        return "<Approve %s>" % self.user_id


ensure_table(Approvals.__table__)

APPROVE_INSERTION_LOCK = threading.RLock()


# is_approved runs for every group message, so keep approvals in memory.
APPROVED = set()


def approve(chat_id, user_id):
    with APPROVE_INSERTION_LOCK:
        try:
            SESSION.merge(Approvals(str(chat_id), user_id))
            SESSION.commit()
        except Exception:
            SESSION.rollback()
            raise
        APPROVED.add((str(chat_id), int(user_id)))


def is_approved(chat_id, user_id):
    return (str(chat_id), int(user_id)) in APPROVED


def disapprove(chat_id, user_id):
    with APPROVE_INSERTION_LOCK:
        APPROVED.discard((str(chat_id), int(user_id)))
        disapprove_user = SESSION.query(Approvals).get((str(chat_id), user_id))
        if disapprove_user:
            SESSION.delete(disapprove_user)
            SESSION.commit()
            return True
        else:
            SESSION.close()
            return False


def list_approved(chat_id):
    try:
        return (
            SESSION.query(Approvals)
            .filter(Approvals.chat_id == str(chat_id))
            .order_by(Approvals.user_id.asc())
            .all()
        )
    finally:
        SESSION.close()


def __load_approvals():
    try:
        APPROVED.update(
            (row.chat_id, int(row.user_id)) for row in SESSION.query(Approvals).all()
        )
    finally:
        SESSION.close()


__load_approvals()
