import html
import threading
from collections import defaultdict, deque
from time import sleep

import anthropic
import IronRobo.modules.sql.chatbot_sql as sql
from IronRobo import AI_API_KEY, AI_MODEL, LOGGER, dispatcher
from IronRobo.modules.helper_funcs.chat_status import user_admin
from IronRobo.modules.helper_funcs.filters import CustomFilters
from IronRobo.modules.log_channel import gloggable
from telegram import Update
from telegram.error import BadRequest, RetryAfter, Unauthorized
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    run_async,
)
from telegram.utils.helpers import mention_html

# Models that accept server-side refusal fallbacks.
FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
HISTORY_LENGTH = 12  # messages kept per chat (user + assistant)

SYSTEM_PROMPT = (
    "You are {name}, a friendly Telegram group assistant bot. You are chatting "
    "inside a Telegram chat; each user message starts with the sender's name. "
    "Reply in the same language the user writes in. Keep replies short and "
    "conversational (a few sentences at most), use plain text without Markdown, "
    "and never pretend to perform moderation actions - admins use bot commands "
    "for that."
)

client = anthropic.Anthropic(api_key=AI_API_KEY, max_retries=2) if AI_API_KEY else None
HISTORY = defaultdict(lambda: deque(maxlen=HISTORY_LENGTH))
HISTORY_LOCK = threading.Lock()


def ask_claude(chat_id, user_name, text, bot_name):
    with HISTORY_LOCK:
        history = HISTORY[chat_id]
        history.append({"role": "user", "content": f"{user_name}: {text}"})
        messages = list(history)
    # The API needs the conversation to start with a user turn.
    while messages and messages[0]["role"] != "user":
        messages.pop(0)

    kwargs = dict(
        model=AI_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT.format(name=bot_name),
        messages=messages,
        output_config={"effort": "low"},
    )
    if AI_MODEL in FALLBACK_MODELS:
        kwargs["betas"] = ["server-side-fallback-2026-07-01"]
        kwargs["fallbacks"] = "default"
        response = client.beta.messages.create(**kwargs)
    else:
        response = client.messages.create(**kwargs)

    if response.stop_reason == "refusal":
        with HISTORY_LOCK:
            HISTORY[chat_id].clear()
        return "I'd rather not answer that one."

    reply = "".join(b.text for b in response.content if b.type == "text").strip()
    if reply:
        with HISTORY_LOCK:
            HISTORY[chat_id].append({"role": "assistant", "content": reply})
    return reply


@run_async
@user_admin
@gloggable
def add_chat(update: Update, context: CallbackContext):
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    if not client:
        msg.reply_text(
            "The chatbot isn't configured. The bot owner needs to set AI_API_KEY "
            "(an Anthropic API key)."
        )
        return ""
    if sql.is_chat(chat.id):
        msg.reply_text("AI is already enabled for this chat!")
        return ""

    sql.set_ses(chat.id, "claude", "0")
    msg.reply_text(
        "AI successfully enabled for this chat! Reply to my messages or mention my "
        "name to talk to me."
    )
    if chat.type == "private":
        return ""
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#AI_ENABLED\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
    )


@run_async
@user_admin
@gloggable
def remove_chat(update: Update, context: CallbackContext):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not sql.is_chat(chat.id):
        msg.reply_text("AI isn't enabled here in the first place!")
        return ""
    sql.rem_chat(chat.id)
    with HISTORY_LOCK:
        HISTORY.pop(chat.id, None)
    msg.reply_text("AI disabled successfully!")
    if chat.type == "private":
        return ""
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#AI_DISABLED\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
    )


def chatbot_toggle(update: Update, context: CallbackContext):
    args = context.args
    if args and args[0].lower() in ("on", "enable", "yes"):
        return add_chat(update, context)
    if args and args[0].lower() in ("off", "disable", "no"):
        return remove_chat(update, context)
    state = "on" if sql.is_chat(update.effective_chat.id) else "off"
    update.effective_message.reply_text(
        f"Chatbot is currently *{state}* here. Use `/chatbot on` or `/chatbot off`.",
        parse_mode="markdown",
    )


def check_message(context: CallbackContext, message):
    if message.chat.type == "private":
        return True
    bot = context.bot
    text = message.text.lower()
    if bot.first_name.lower() in text or f"@{bot.username.lower()}" in text:
        return True
    reply_msg = message.reply_to_message
    return bool(reply_msg and reply_msg.from_user and reply_msg.from_user.id == bot.id)


@run_async
def chatbot(update: Update, context: CallbackContext):
    msg = update.effective_message
    chat_id = update.effective_chat.id
    if not client or not msg or not msg.text:
        return
    if not sql.is_chat(chat_id):
        return
    if not check_message(context, msg):
        return

    bot = context.bot
    user = update.effective_user
    try:
        bot.send_chat_action(chat_id, action="typing")
        reply = ask_claude(
            chat_id, user.first_name if user else "Someone", msg.text, bot.first_name
        )
    except anthropic.AuthenticationError:
        LOGGER.error("Chatbot: AI_API_KEY was rejected by the Anthropic API")
        return
    except anthropic.RateLimitError:
        msg.reply_text("I'm getting too many messages right now, try again in a bit.")
        return
    except anthropic.APIError as e:
        LOGGER.warning("Chatbot API error in %s: %s", chat_id, e)
        return
    if reply:
        msg.reply_text(reply[:4096], timeout=60)


@run_async
def list_chatbot_chats(update: Update, context: CallbackContext):
    chats = sql.get_all_chats()
    text = "<b>AI-Enabled Chats</b>\n"
    for chat in chats:
        try:
            x = context.bot.get_chat(int(*chat))
            name = x.title or x.first_name
            text += f"• <code>{html.escape(name)}</code>\n"
        except (BadRequest, Unauthorized):
            sql.rem_chat(*chat)
        except RetryAfter as e:
            sleep(e.retry_after)
    update.effective_message.reply_text(text, parse_mode="HTML")


__help__ = """
Chat with the bot, powered by Claude (the owner has to set `AI_API_KEY`).

 • `/chatbot on|off`*:* Enables or disables the chatbot in this chat
 • `/addchat`*:* Same as `/chatbot on`
 • `/rmchat`*:* Same as `/chatbot off`

When it's on, reply to one of my messages or mention my name to talk to me.
In private chat every message gets an answer.
"""

ADD_CHAT_HANDLER = CommandHandler("addchat", add_chat)
REMOVE_CHAT_HANDLER = CommandHandler("rmchat", remove_chat)
TOGGLE_HANDLER = CommandHandler("chatbot", chatbot_toggle, run_async=True)
# Ignore commands, #notes and !commands.
CHATBOT_HANDLER = MessageHandler(
    Filters.text
    & ~Filters.command
    & ~Filters.regex(r"^#[^\s]+")
    & ~Filters.regex(r"^!")
    & ~Filters.regex(r"^\/"),
    chatbot,
)
LIST_CB_CHATS_HANDLER = CommandHandler(
    "listaichats", list_chatbot_chats, filters=CustomFilters.dev_filter
)

CHATBOT_GROUP = 15

dispatcher.add_handler(ADD_CHAT_HANDLER)
dispatcher.add_handler(REMOVE_CHAT_HANDLER)
dispatcher.add_handler(TOGGLE_HANDLER)
dispatcher.add_handler(CHATBOT_HANDLER, CHATBOT_GROUP)
dispatcher.add_handler(LIST_CB_CHATS_HANDLER)

__mod_name__ = "Chatbot"
__command_list__ = ["addchat", "rmchat", "chatbot", "listaichats"]
__handlers__ = [
    ADD_CHAT_HANDLER,
    REMOVE_CHAT_HANDLER,
    TOGGLE_HANDLER,
    (CHATBOT_HANDLER, CHATBOT_GROUP),
    LIST_CB_CHATS_HANDLER,
]
