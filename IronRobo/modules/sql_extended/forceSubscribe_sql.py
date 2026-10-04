from sqlalchemy import Column, String, Numeric, Boolean
from IronRobo.modules.sql import BASE, SESSION, ensure_table


class forceSubscribe(BASE):
    __tablename__ = "forceSubscribe"
    chat_id = Column(Numeric, primary_key=True)
    channel = Column(String)

    def __init__(self, chat_id, channel):
        self.chat_id = chat_id
        self.channel = channel


ensure_table(forceSubscribe.__table__)


def fs_settings(chat_id):
    try:
        return SESSION.query(forceSubscribe).filter(forceSubscribe.chat_id == chat_id).one()
    except:
        return None
    finally:
        SESSION.close()


def add_channel(chat_id, channel):
    adder = SESSION.query(forceSubscribe).get(chat_id)
    if adder:
        adder.channel = channel
    else:
        adder = forceSubscribe(
            chat_id,
            channel
        )
    SESSION.add(adder)
    SESSION.commit()

def disapprove(chat_id):
    rem = SESSION.query(forceSubscribe).get(chat_id)
    if rem:
        SESSION.delete(rem)
        SESSION.commit()
