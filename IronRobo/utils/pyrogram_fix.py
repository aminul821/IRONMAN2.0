"""Clock handling fixes for Pyrogram 1.4.

Pyrogram 1.4 builds message ids from an uptime counter until the server
reports its time, so the very first request of a session carries an id that
Telegram rejects ("[16] The msg_id is too low"). It also gives up instead of
retrying once the server has told it the correct time, so a machine whose
clock is a little off can never connect.

This module seeds the message id clock with the wall clock, lets the server
time correct it when the two disagree, and retries the session handshake
after a time correction.
"""
import logging
from time import perf_counter, time

from pyrogram.errors import BadMsgNotification
from pyrogram.session import Session
from pyrogram.session.internals.msg_id import MsgId

log = logging.getLogger(__name__)

# Resync with the server clock when we are off by more than this many seconds.
MAX_DRIFT = 5


def _seed_clock():
    MsgId.reference_clock = perf_counter()
    MsgId.server_time = time()
    MsgId.last_time = 0


@classmethod
def _set_server_time(cls, server_time: float):
    now = perf_counter() - cls.reference_clock + cls.server_time
    if abs(server_time - now) > MAX_DRIFT:
        log.info("Correcting Pyrogram clock by %.1f seconds", server_time - now)
        cls.reference_clock = perf_counter()
        cls.server_time = server_time


_original_start = Session.start


async def _start(self):
    attempts = 3
    for attempt in range(1, attempts + 1):
        try:
            return await _original_start(self)
        except BadMsgNotification as e:
            # 16/17: msg_id too low/high. The server's reply already
            # corrected our clock, so trying again works.
            if attempt == attempts or ("[16]" not in str(e) and "[17]" not in str(e)):
                raise
            log.warning("Telegram rejected the client time (%s), retrying", e)


def apply():
    _seed_clock()
    MsgId.set_server_time = _set_server_time
    Session.start = _start
