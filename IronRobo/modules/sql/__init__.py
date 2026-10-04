from IronRobo import DB_URI, LOGGER
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker


def _upgrade_id_columns(engine):
    """Widen Telegram user id columns from INTEGER to BIGINT.

    Newer Telegram accounts have ids above 2^31, which don't fit in the
    INTEGER columns older versions of this bot created.
    """
    query = text(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND data_type = 'integer' "
        "AND (column_name = 'user_id' "
        "OR (table_name = 'chat_members' AND column_name = 'user'))"
    )
    with engine.begin() as conn:
        for table, column in conn.execute(query).fetchall():
            LOGGER.info("Upgrading %s.%s to BIGINT", table, column)
            conn.execute(
                text(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE BIGINT')
            )


def start() -> scoped_session:
    engine_kwargs = {"pool_pre_ping": True}
    if DB_URI.startswith("postgresql"):
        engine_kwargs["client_encoding"] = "utf8"
    engine = create_engine(DB_URI, **engine_kwargs)
    if DB_URI.startswith("postgresql"):
        _upgrade_id_columns(engine)
    BASE.metadata.bind = engine
    BASE.metadata.create_all(engine)
    return scoped_session(sessionmaker(bind=engine, autoflush=False))


BASE = declarative_base()
SESSION = start()


# The bot handles updates in long-lived worker threads, each with its own
# scoped session. If a query fails, that session is left in a failed
# transaction and every later query on the thread errors too. Resetting the
# thread's session after each update keeps one bad query from breaking the
# worker for good.
def _reset_session_after(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        finally:
            SESSION.remove()

    wrapper.__wrapped__ = func
    return wrapper


def _install_session_reset():
    from telegram.ext import Dispatcher
    from telegram.ext.utils.promise import Promise

    if not hasattr(Dispatcher.process_update, "__wrapped__"):
        Dispatcher.process_update = _reset_session_after(Dispatcher.process_update)
    if not hasattr(Promise.run, "__wrapped__"):
        Promise.run = _reset_session_after(Promise.run)


_install_session_reset()
