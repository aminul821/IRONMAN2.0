import threading

from sqlalchemy import Column, String, UnicodeText, Boolean, Integer, distinct, func

from IronRobo.modules.helper_funcs.msg_types import Types
from IronRobo.modules.sql import BASE, SESSION, ensure_table


class CustomFilters(BASE):
    __tablename__ = "cust_filters"
    chat_id = Column(String(14), primary_key=True)
    keyword = Column(UnicodeText, primary_key=True, nullable=False)
    reply = Column(UnicodeText, nullable=False)
    is_sticker = Column(Boolean, nullable=False, default=False)
    is_document = Column(Boolean, nullable=False, default=False)
    is_image = Column(Boolean, nullable=False, default=False)
    is_audio = Column(Boolean, nullable=False, default=False)
    is_voice = Column(Boolean, nullable=False, default=False)
    is_video = Column(Boolean, nullable=False, default=False)

    has_buttons = Column(Boolean, nullable=False, default=False)
    # NOTE: Here for legacy purposes, to ensure older filters don't mess up.
    has_markdown = Column(Boolean, nullable=False, default=False)

    # NEW FILTER
    # alter table cust_filters add column reply_text text;
    # alter table cust_filters add column file_type integer default 1;
    # alter table cust_filters add column file_id text;
    reply_text = Column(UnicodeText)
    file_type = Column(Integer, nullable=False, default=1)
    file_id = Column(UnicodeText, default=None)

    def __init__(
        self,
        chat_id,
        keyword,
        reply,
        is_sticker=False,
        is_document=False,
        is_image=False,
        is_audio=False,
        is_voice=False,
        is_video=False,
        has_buttons=False,
        reply_text=None,
        file_type=1,
        file_id=None,
    ):
        self.chat_id = str(chat_id)  # ensure string
        self.keyword = keyword
        self.reply = reply
        self.is_sticker = is_sticker
        self.is_document = is_document
        self.is_image = is_image
        self.is_audio = is_audio
        self.is_voice = is_voice
        self.is_video = is_video
        self.has_buttons = has_buttons
        self.has_markdown = True

        self.reply_text = reply_text
        self.file_type = file_type
        self.file_id = file_id

    def __repr__(self):
        return "<Permissions for %s>" % self.chat_id

    def __eq__(self, other):
        return bool(
            isinstance(other, CustomFilters)
            and self.chat_id == other.chat_id
            and self.keyword == other.keyword
        )


class NewCustomFilters(BASE):
    __tablename__ = "cust_filters_new"
    chat_id = Column(String(14), primary_key=True)
    keyword = Column(UnicodeText, primary_key=True, nullable=False)
    text = Column(UnicodeText)
    file_type = Column(Integer, nullable=False, default=1)
    file_id = Column(UnicodeText, default=None)

    def __init__(self, chat_id, keyword, text, file_type, file_id):
        self.chat_id = str(chat_id)  # ensure string
        self.keyword = keyword
        self.text = text
        self.file_type = file_type
        self.file_id = file_id

    def __repr__(self):
        return "<Filter for %s>" % self.chat_id

    def __eq__(self, other):
        return bool(
            isinstance(other, CustomFilters)
            and self.chat_id == other.chat_id
            and self.keyword == other.keyword
        )


class Buttons(BASE):
    __tablename__ = "cust_filter_urls"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(14), primary_key=True)
    keyword = Column(UnicodeText, primary_key=True)
    name = Column(UnicodeText, nullable=False)
    url = Column(UnicodeText, nullable=False)
    same_line = Column(Boolean, default=False)

    def __init__(self, chat_id, keyword, name, url, same_line=False):
        self.chat_id = str(chat_id)
        self.keyword = keyword
        self.name = name
        self.url = url
        self.same_line = same_line


ensure_table(CustomFilters.__table__)
ensure_table(Buttons.__table__)

CUST_FILT_LOCK = threading.RLock()
BUTTON_LOCK = threading.RLock()
CHAT_FILTERS = {}


def get_all_filters():
    try:
        return SESSION.query(CustomFilters).all()
    finally:
        SESSION.close()


def add_filter(
    chat_id,
    keyword,
    reply,
    is_sticker=False,
    is_document=False,
    is_image=False,
    is_audio=False,
    is_voice=False,
    is_video=False,
    buttons=None,
):
    _invalidate(chat_id, keyword)
    global CHAT_FILTERS

    if buttons is None:
        buttons = []

    with CUST_FILT_LOCK:
        prev = SESSION.query(CustomFilters).get((str(chat_id), keyword))
        if prev:
            with BUTTON_LOCK:
                prev_buttons = (
                    SESSION.query(Buttons)
                    .filter(Buttons.chat_id == str(chat_id), Buttons.keyword == keyword)
                    .all()
                )
                for btn in prev_buttons:
                    SESSION.delete(btn)
            SESSION.delete(prev)

        filt = CustomFilters(
            str(chat_id),
            keyword,
            reply,
            is_sticker,
            is_document,
            is_image,
            is_audio,
            is_voice,
            is_video,
            bool(buttons),
        )

        if keyword not in CHAT_FILTERS.get(str(chat_id), []):
            CHAT_FILTERS[str(chat_id)] = sorted(
                CHAT_FILTERS.get(str(chat_id), []) + [keyword],
                key=lambda x: (-len(x), x),
            )

        SESSION.add(filt)
        SESSION.commit()

    for b_name, url, same_line in buttons:
        add_note_button_to_db(chat_id, keyword, b_name, url, same_line)


def new_add_filter(chat_id, keyword, reply_text, file_type, file_id, buttons):
    _invalidate(chat_id, keyword)
    global CHAT_FILTERS

    if buttons is None:
        buttons = []

    with CUST_FILT_LOCK:
        prev = SESSION.query(CustomFilters).get((str(chat_id), keyword))
        if prev:
            with BUTTON_LOCK:
                prev_buttons = (
                    SESSION.query(Buttons)
                    .filter(Buttons.chat_id == str(chat_id), Buttons.keyword == keyword)
                    .all()
                )
                for btn in prev_buttons:
                    SESSION.delete(btn)
            SESSION.delete(prev)

        filt = CustomFilters(
            str(chat_id),
            keyword,
            reply="there is should be a new reply",
            is_sticker=False,
            is_document=False,
            is_image=False,
            is_audio=False,
            is_voice=False,
            is_video=False,
            has_buttons=bool(buttons),
            reply_text=reply_text,
            file_type=file_type.value,
            file_id=file_id,
        )

        if keyword not in CHAT_FILTERS.get(str(chat_id), []):
            CHAT_FILTERS[str(chat_id)] = sorted(
                CHAT_FILTERS.get(str(chat_id), []) + [keyword],
                key=lambda x: (-len(x), x),
            )

        SESSION.add(filt)
        SESSION.commit()

    for b_name, url, same_line in buttons:
        add_note_button_to_db(chat_id, keyword, b_name, url, same_line)


def remove_filter(chat_id, keyword):
    _invalidate(chat_id, keyword)
    global CHAT_FILTERS
    with CUST_FILT_LOCK:
        filt = SESSION.query(CustomFilters).get((str(chat_id), keyword))
        if filt:
            if keyword in CHAT_FILTERS.get(str(chat_id), []):  # Sanity check
                CHAT_FILTERS.get(str(chat_id), []).remove(keyword)

            with BUTTON_LOCK:
                prev_buttons = (
                    SESSION.query(Buttons)
                    .filter(Buttons.chat_id == str(chat_id), Buttons.keyword == keyword)
                    .all()
                )
                for btn in prev_buttons:
                    SESSION.delete(btn)

            SESSION.delete(filt)
            SESSION.commit()
            return True

        SESSION.close()
        return False


def get_chat_triggers(chat_id):
    return CHAT_FILTERS.get(str(chat_id), set())


def get_chat_filters(chat_id):
    try:
        return (
            SESSION.query(CustomFilters)
            .filter(CustomFilters.chat_id == str(chat_id))
            .order_by(func.length(CustomFilters.keyword).desc())
            .order_by(CustomFilters.keyword.asc())
            .all()
        )
    finally:
        SESSION.close()


# reply_filter looks a filter and its buttons up every time it triggers;
# keep them in memory so a match doesn't wait on the database.
_FILTER_CACHE = {}
_BUTTON_CACHE = {}
_CACHE_LOCK = threading.RLock()


def _invalidate(chat_id, keyword=None):
    with _CACHE_LOCK:
        if keyword is None:
            for cache in (_FILTER_CACHE, _BUTTON_CACHE):
                for key in [k for k in cache if k[0] == str(chat_id)]:
                    del cache[key]
        else:
            _FILTER_CACHE.pop((str(chat_id), keyword), None)
            _BUTTON_CACHE.pop((str(chat_id), keyword), None)


def get_filter(chat_id, keyword):
    key = (str(chat_id), keyword)
    with _CACHE_LOCK:
        if key in _FILTER_CACHE:
            return _FILTER_CACHE[key]
    try:
        filt = SESSION.query(CustomFilters).get(key)
        if filt is not None:
            SESSION.expunge(filt)
    finally:
        SESSION.close()
    with _CACHE_LOCK:
        _FILTER_CACHE[key] = filt
    return filt


def add_note_button_to_db(chat_id, keyword, b_name, url, same_line):
    _invalidate(chat_id, keyword)
    with BUTTON_LOCK:
        button = Buttons(chat_id, keyword, b_name, url, same_line)
        SESSION.add(button)
        SESSION.commit()


def get_buttons(chat_id, keyword):
    key = (str(chat_id), keyword)
    with _CACHE_LOCK:
        if key in _BUTTON_CACHE:
            return _BUTTON_CACHE[key]
    try:
        buttons = (
            SESSION.query(Buttons)
            .filter(Buttons.chat_id == str(chat_id), Buttons.keyword == keyword)
            .order_by(Buttons.id)
            .all()
        )
        for btn in buttons:
            SESSION.expunge(btn)
    finally:
        SESSION.close()
    with _CACHE_LOCK:
        _BUTTON_CACHE[key] = buttons
    return buttons


def _clear_cache_after(func):
    """Also drop the cache after the change, so a reader can't re-cache old data."""

    def wrapper(chat_id, keyword, *args, **kwargs):
        try:
            return func(chat_id, keyword, *args, **kwargs)
        finally:
            _invalidate(chat_id, keyword)

    return wrapper


add_filter = _clear_cache_after(add_filter)
new_add_filter = _clear_cache_after(new_add_filter)
remove_filter = _clear_cache_after(remove_filter)
add_note_button_to_db = _clear_cache_after(add_note_button_to_db)


def num_filters():
    try:
        return SESSION.query(CustomFilters).count()
    finally:
        SESSION.close()


def num_chats():
    try:
        return SESSION.query(func.count(distinct(CustomFilters.chat_id))).scalar()
    finally:
        SESSION.close()


def __load_chat_filters():
    global CHAT_FILTERS
    try:
        chats = SESSION.query(CustomFilters.chat_id).distinct().all()
        for (chat_id,) in chats:  # remove tuple by ( ,)
            CHAT_FILTERS[chat_id] = []

        all_filters = SESSION.query(CustomFilters).all()
        for x in all_filters:
            CHAT_FILTERS[x.chat_id] += [x.keyword]

        CHAT_FILTERS = {
            x: sorted(set(y), key=lambda i: (-len(i), i))
            for x, y in CHAT_FILTERS.items()
        }

    finally:
        SESSION.close()


# ONLY USE FOR MIGRATE OLD FILTERS TO NEW FILTERS
def __migrate_filters():
    try:
        all_filters = SESSION.query(CustomFilters).distinct().all()
        for x in all_filters:
            if x.is_document:
                file_type = Types.DOCUMENT
            elif x.is_image:
                file_type = Types.PHOTO
            elif x.is_video:
                file_type = Types.VIDEO
            elif x.is_sticker:
                file_type = Types.STICKER
            elif x.is_audio:
                file_type = Types.AUDIO
            elif x.is_voice:
                file_type = Types.VOICE
            else:
                file_type = Types.TEXT

            print(str(x.chat_id), x.keyword, x.reply, file_type.value)
            if file_type == Types.TEXT:
                filt = CustomFilters(
                    str(x.chat_id), x.keyword, x.reply, file_type.value, None
                )
            else:
                filt = CustomFilters(
                    str(x.chat_id), x.keyword, None, file_type.value, x.reply
                )

            SESSION.add(filt)
            SESSION.commit()

    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    _invalidate(old_chat_id)
    with CUST_FILT_LOCK:
        chat_filters = (
            SESSION.query(CustomFilters)
            .filter(CustomFilters.chat_id == str(old_chat_id))
            .all()
        )
        for filt in chat_filters:
            filt.chat_id = str(new_chat_id)
        SESSION.commit()
        old_filt = CHAT_FILTERS.get(str(old_chat_id))
        if old_filt:
            CHAT_FILTERS[str(new_chat_id)] = old_filt
            del CHAT_FILTERS[str(old_chat_id)]

        with BUTTON_LOCK:
            chat_buttons = (
                SESSION.query(Buttons).filter(Buttons.chat_id == str(old_chat_id)).all()
            )
            for btn in chat_buttons:
                btn.chat_id = str(new_chat_id)
            SESSION.commit()


__load_chat_filters()
