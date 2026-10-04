"""Import a group's settings from a Miss Rose (@MissRose_bot) /export file."""
import html
import json
import time
from io import BytesIO

import IronRobo.modules.sql.antiflood_sql as flood_sql
import IronRobo.modules.sql.blacklist_sql as blacklist_sql
import IronRobo.modules.sql.cust_filters_sql as filters_sql
import IronRobo.modules.sql.disable_sql as disable_sql
import IronRobo.modules.sql.locks_sql as locks_sql
import IronRobo.modules.sql.notes_sql as notes_sql
import IronRobo.modules.sql.reporting_sql as reporting_sql
import IronRobo.modules.sql.rules_sql as rules_sql
import IronRobo.modules.sql.warns_sql as warns_sql
import IronRobo.modules.sql.welcome_sql as welcome_sql
from IronRobo import LOGGER, dispatcher
from IronRobo.modules.helper_funcs.chat_status import user_admin
from IronRobo.modules.helper_funcs.msg_types import Types
from IronRobo.modules.helper_funcs.string_handling import button_markdown_parser
from telegram import ParseMode, Update
from telegram.error import BadRequest, RetryAfter, TelegramError
from telegram.ext import CallbackContext, CommandHandler

# Telegram file ids start with an encoded file type.
FILE_ID_PREFIXES = {
    "CAAC": Types.STICKER,
    "CgAC": Types.ANIMATION,
    "BAAC": Types.VIDEO,
    "AwAC": Types.VOICE,
    "AgAC": Types.PHOTO,
    "BQAC": Types.DOCUMENT,
    "CQAC": Types.AUDIO,
    "DQAC": Types.VIDEO_NOTE,
}

# Rose lock name -> IronRobo message lock (message gets deleted)
MESSAGE_LOCKS = {
    "audio": "audio",
    "voice": "voice",
    "document": "document",
    "video": "video",
    "contact": "contact",
    "photo": "photo",
    "url": "url",
    "bot": "bots",
    "forward": "forward",
    "game": "game",
    "location": "location",
    "rtl": "rtl",
    "button": "button",
    "inline": "inline",
    "emojigame": "egame",
}
# Rose lock name -> chat permission that IronRobo turns off
PERMISSION_LOCKS = {
    "all": {
        "can_send_messages": False,
        "can_send_media_messages": False,
        "can_send_polls": False,
        "can_send_other_messages": False,
        "can_add_web_page_previews": False,
    },
    "text": {"can_send_messages": False},
    "sticker": {"can_send_other_messages": False},
    "gif": {"can_send_other_messages": False},
    "poll": {"can_send_polls": False},
}
# IronRobo blacklist modes: 0 nothing, 1 delete, 2 warn, 3 mute, 4 kick,
# 5 ban, 6 tban, 7 tmute.
BLACKLIST_ACTIONS = {"warn": 2, "mute": 3, "kick": 4, "ban": 5, "tban": 6, "tmute": 7}
# IronRobo flood modes: 1 ban, 2 kick, 3 mute, 4 tban, 5 tmute.
FLOOD_ACTIONS = {"ban": 1, "kick": 2, "mute": 3, "tban": 4, "tmute": 5}


def media_type(item):
    """IronRobo message type for a Rose filter/note/greeting entry."""
    file_id = item.get("data_id") or ""
    if not file_id:
        return None
    return FILE_ID_PREFIXES.get(file_id[:4], Types.DOCUMENT)


def clean_text(text):
    text = (text or "").strip()
    return text


def duration_text(seconds):
    """Rose stores durations in seconds; IronRobo wants e.g. 30m, 2h, 1d."""
    seconds = int(seconds or 0)
    if seconds <= 0:
        return ""
    if seconds % 86400 == 0:
        return f"{seconds // 86400}d"
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    return f"{max(1, -(-seconds // 60))}m"


def usable_file(bot, file_id):
    """True if this bot can send the file (file ids from other bots may not work)."""
    for _ in range(3):
        try:
            bot.get_file(file_id)
            return True
        except RetryAfter as e:
            time.sleep(e.retry_after + 1)
        except BadRequest as e:
            # still a valid id, just too big to download
            return "too big" in e.message.lower()
        except TelegramError:
            return False
    return False


class Report:
    def __init__(self):
        self.done = []
        self.skipped = []

    def add(self, text):
        self.done.append(text)

    def skip(self, text):
        self.skipped.append(text)


def import_entries(bot, chat_id, entries, kind, report, save):
    imported, unusable = 0, []
    for item in entries or []:
        name = (item.get("name") or "").strip().lower()
        if not name:
            continue
        text, buttons = button_markdown_parser(clean_text(item.get("text")))
        file_type = media_type(item)
        file_id = item.get("data_id") or None
        if file_type is not None:
            if not usable_file(bot, file_id):
                unusable.append(name)
                continue
        else:
            if not text:
                continue
            file_type = Types.BUTTON_TEXT if buttons else Types.TEXT
        save(chat_id, name, text, file_type, file_id, buttons)
        imported += 1
    if imported:
        report.add(f"{imported} {kind}")
    if unusable:
        report.skip(
            f"{len(unusable)} {kind} with a sticker/media that I can't send "
            f"(re-add them by replying to the media): {', '.join(unusable)}"
        )


def save_filter(chat_id, name, text, file_type, file_id, buttons):
    filters_sql.new_add_filter(chat_id, name, text, file_type, file_id, buttons)


def save_note(chat_id, name, text, file_type, file_id, buttons):
    notes_sql.add_note_to_db(chat_id, name, text, file_type, buttons=buttons, file=file_id)


def import_greeting(bot, chat_id, data, report):
    greetings = data.get("greetings") or {}
    if not greetings:
        return
    welcome_sql.set_welc_preference(str(chat_id), bool(greetings.get("should_welcome", True)))
    welcome_sql.set_gdbye_preference(str(chat_id), bool(greetings.get("should_goodbye", True)))
    welcome_sql.set_clean_welcome(str(chat_id), bool(greetings.get("should_clean")))
    if greetings.get("should_mute"):
        mode = "strong" if greetings.get("mute_mode") == "button" else "soft"
        welcome_sql.set_welcome_mutes(chat_id, mode)
    else:
        welcome_sql.set_welcome_mutes(chat_id, False)

    for key, setter, label in (
        ("welcome", welcome_sql.set_custom_welcome, "welcome message"),
        ("goodbye", None, "goodbye message"),
    ):
        entry = greetings.get(key) or {}
        text, buttons = button_markdown_parser(clean_text(entry.get("text")))
        file_type = media_type(entry)
        file_id = entry.get("data_id") or None
        if file_type is None and not text:
            continue  # Rose default, keep ours
        if file_type is not None and not usable_file(bot, file_id):
            report.skip(f"the {label} (its media can't be sent by me)")
            continue
        if file_type is None:
            file_type = Types.BUTTON_TEXT if buttons else Types.TEXT
        if key == "welcome":
            setter(chat_id, file_id, text, file_type, buttons)
        else:
            content = file_id if file_type not in (Types.TEXT, Types.BUTTON_TEXT) else text
            welcome_sql.set_custom_gdbye(chat_id, content, file_type, buttons)
        report.add(label)

    service = (data.get("clean_service") or {}).get("service_types") or {}
    join_clean = (service.get("join") or {}).get("clean") or (service.get("all") or {}).get("clean")
    welcome_sql.set_clean_service(chat_id, bool(join_clean))
    report.add("welcome settings")


def import_locks(bot, chat_id, data, report):
    locks = ((data.get("locks") or {}).get("locks")) or {}
    locked = [name for name, value in locks.items() if (value or {}).get("locked")]
    if not locked:
        return
    applied, unsupported = [], []
    permissions = {}
    for name in locked:
        if name in MESSAGE_LOCKS:
            locks_sql.update_lock(chat_id, MESSAGE_LOCKS[name], locked=True)
            applied.append(name)
        elif name in PERMISSION_LOCKS:
            permissions.update(PERMISSION_LOCKS[name])
            applied.append(name)
        else:
            unsupported.append(name)
    if permissions:
        try:
            current = bot.get_chat(chat_id).permissions
            current = current.to_dict() if current else {}
            current.update(permissions)
            from telegram import ChatPermissions

            bot.set_chat_permissions(chat_id, ChatPermissions(**current))
        except TelegramError as e:
            report.skip(f"sticker/gif/text/poll locks ({e.message})")
    if applied:
        report.add(f"locks: {', '.join(applied)}")
    if unsupported:
        report.skip(f"locks I don't have: {', '.join(unsupported)}")


def import_rose(bot, chat_id, data):
    report = Report()

    # filters & notes
    import_entries(bot, chat_id, (data.get("filters") or {}).get("filters"), "filters", report, save_filter)
    import_entries(bot, chat_id, (data.get("notes") or {}).get("notes"), "notes", report, save_note)

    # rules
    rules = clean_text((data.get("rules") or {}).get("content"))
    if rules:
        rules_sql.set_rules(chat_id, rules)
        report.add("rules")

    # blocklist -> blacklist
    blocklists = data.get("blocklists") or {}
    words = [
        (b.get("name") or "").strip().lower()
        for b in blocklists.get("filters") or []
        if (b.get("name") or "").strip()
    ]
    for word in words:
        blacklist_sql.add_to_blacklist(chat_id, word)
    if words or blocklists.get("action"):
        action = blocklists.get("action") or "nothing"
        if action in BLACKLIST_ACTIONS:
            mode = BLACKLIST_ACTIONS[action]
        else:
            mode = 1 if blocklists.get("should_delete", True) else 0
        blacklist_sql.set_blacklist_strength(
            chat_id, mode, duration_text(blocklists.get("action_duration")) or "0"
        )
        report.add(f"{len(words)} blacklisted words")

    # antiflood
    flood = data.get("antiflood") or {}
    if flood:
        limit = int(flood.get("flood_limit") or 0)
        flood_sql.set_flood(chat_id, limit)
        action = flood.get("action") or "mute"
        if action in FLOOD_ACTIONS:
            flood_sql.set_flood_strength(
                chat_id, FLOOD_ACTIONS[action], duration_text(flood.get("action_duration")) or "0"
            )
        report.add(f"antiflood ({limit or 'off'}, {action})")

    # warns
    warns = data.get("warns") or {}
    if warns:
        if warns.get("warn_limit"):
            warns_sql.set_warn_limit(chat_id, int(warns["warn_limit"]))
        action = warns.get("action") or "ban"
        if action in ("ban", "tban"):
            warns_sql.set_warn_strength(chat_id, False)
        elif action == "kick":
            warns_sql.set_warn_strength(chat_id, True)
        else:
            report.skip(f"warn action '{action}' (I can only kick or ban, kept ban)")
            warns_sql.set_warn_strength(chat_id, False)
        report.add(f"warn limit {warns.get('warn_limit')} ({action})")

    import_greeting(bot, chat_id, data, report)
    import_locks(bot, chat_id, data, report)

    # disabled commands
    disabled = (data.get("disabled") or {}).get("disabled") or []
    for cmd in disabled:
        disable_sql.disable_command(chat_id, str(cmd).lower())
    if disabled:
        report.add(f"{len(disabled)} disabled commands")

    # reports
    reports = data.get("reports") or {}
    if "disable_reports" in reports:
        reporting_sql.set_chat_setting(chat_id, not reports["disable_reports"])
        report.add("report setting")

    return report


@user_admin
def importrose(update: Update, context: CallbackContext):
    msg = update.effective_message
    chat = update.effective_chat
    if chat.type == "private":
        msg.reply_text("Use this in the group you want to import the settings into.")
        return
    doc = msg.reply_to_message.document if msg.reply_to_message else None
    if not doc:
        msg.reply_text(
            "Send /export in this group while Rose is here, then reply to her file with /importrose."
        )
        return
    if doc.file_size and doc.file_size > 5 * 1024 * 1024:
        msg.reply_text("That file is too big to be a Rose export.")
        return
    try:
        buf = BytesIO()
        context.bot.get_file(doc.file_id).download(out=buf)
        export = json.loads(buf.getvalue().decode("utf-8"))
        data = export["data"]
        assert isinstance(data, dict)
    except (ValueError, KeyError, AssertionError, UnicodeDecodeError):
        msg.reply_text("That doesn't look like a Rose export file.")
        return

    status = msg.reply_text("Importing Rose's settings, this can take a minute...")
    try:
        report = import_rose(context.bot, chat.id, data)
    except Exception:
        LOGGER.exception("Rose import failed in %s", chat.id)
        status.edit_text("Something went wrong while importing, part of the settings may have been imported.")
        return

    text = "<b>Imported from Rose:</b>\n" + "\n".join(
        f"• {html.escape(x)}" for x in report.done
    )
    if report.skipped:
        text += "\n\n<b>Not imported:</b>\n" + "\n".join(
            f"• {html.escape(x)}" for x in report.skipped
        )
    if len(text) > 4000:
        text = text[:3990] + "…"
    status.edit_text(text, parse_mode=ParseMode.HTML)


IMPORTROSE_HANDLER = CommandHandler("importrose", importrose, run_async=True)
dispatcher.add_handler(IMPORTROSE_HANDLER)

__mod_name__ = "Rose Import"
__help__ = """
Move a group from Rose to me.

 • Send `/export` in your group while @MissRose_bot is there; she replies with a file.
 • Reply to that file with `/importrose` (admins only).

I copy filters, notes, rules, the blocklist, antiflood, warn settings, welcome/goodbye, locks, disabled commands and the report setting.
Filters or notes whose sticker/media I can't send are listed so you can add them again.
"""
__command_list__ = ["importrose"]
__handlers__ = [IMPORTROSE_HANDLER]
