import html

from IronRobo import pbot as app
from IronRobo.modules.sql_extended import karma_sql as sql
from IronRobo.utils.errors import capture_err
from IronRobo.utils.filter_groups import karma_negative_group, karma_positive_group
from pyrogram import filters

regex_upvote = r"(?i)^(\+|\+\+|\+1|thx|tnx|ty|thank you|thanx|thanks|pro|cool|good|👍)$"
regex_downvote = r"^(\-|\-\-|\-1|👎)$"


async def _vote(message, amount):
    reply = message.reply_to_message
    if not reply.from_user or not message.from_user:
        return
    if reply.from_user.id == message.from_user.id or reply.from_user.is_bot:
        return
    karma = sql.change_karma(message.chat.id, reply.from_user.id, amount)
    action = "Incremented" if amount > 0 else "Decremented"
    await message.reply_text(
        f"{action} Karma of {reply.from_user.mention} By 1 \nTotal Points: {karma}"
    )


@app.on_message(
    filters.text
    & filters.group
    & filters.incoming
    & filters.reply
    & filters.regex(regex_upvote)
    & ~filters.via_bot
    & ~filters.bot
    & ~filters.edited,
    group=karma_positive_group,
)
@capture_err
async def upvote(_, message):
    await _vote(message, 1)


@app.on_message(
    filters.text
    & filters.group
    & filters.incoming
    & filters.reply
    & filters.regex(regex_downvote)
    & ~filters.via_bot
    & ~filters.bot
    & ~filters.edited,
    group=karma_negative_group,
)
@capture_err
async def downvote(_, message):
    await _vote(message, -1)


@app.on_message(filters.command("karma") & filters.group)
@capture_err
async def karma(_, message):
    chat_id = message.chat.id

    if message.reply_to_message and message.reply_to_message.from_user:
        points = sql.get_karma(chat_id, message.reply_to_message.from_user.id)
        await message.reply_text(f"**Total Points**: __{points}__")
        return

    top = sql.top_karma(chat_id, 10)
    if not top:
        await message.reply_text("Nobody has any karma in this chat yet.")
        return
    msg = f"<b>Karma list of {html.escape(message.chat.title or 'this chat')}:</b>\n"
    for user_id, points in top:
        try:
            user = await app.get_users(user_id)
            name = html.escape(user.first_name or str(user_id))
        except Exception:
            name = str(user_id)
        msg += f"{name} : <code>{points}</code>\n"
    await message.reply_text(msg, parse_mode="html")


def __stats__():
    chats, total = sql.karma_stats()
    return f"• {total} karma points, across {chats} chats."


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


__help__ = """
*Karma:*
Reply to someone with `+`, `+1`, `thanks`, `👍` ... to give them karma, or with `-`, `-1`, `👎` to take one away.

 • `/karma`*:* Shows the top karma holders of the chat
 • `/karma`*:* (as a reply) Shows the karma of that user
"""
__mod_name__ = "Karma"
