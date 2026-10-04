
import html
from telegram import Message, Update, Bot, User, Chat, ParseMode
from typing import List, Optional
from telegram.error import BadRequest, TelegramError
from telegram.ext import CallbackContext, CommandHandler
from telegram.utils.helpers import mention_html
from IronRobo import dispatcher, OWNER_ID, DEV_USERS, DRAGONS, STRICT_GBAN
from IronRobo.modules.helper_funcs.chat_status import user_admin, is_user_admin
from IronRobo.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from IronRobo.modules.helper_funcs.filters import CustomFilters
from IronRobo.modules.helper_funcs.misc import send_to_list
from IronRobo.modules.sql.users_sql import get_all_chats

GKICK_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Peer_id_invalid",
    "Group chat was deactivated",
    "Need to be inviter of a user to kick it from a basic group",
    "Chat_admin_required",
    "Only the creator of a basic group can kick group administrators",
    "Channel_private",
    "Not in the chat",
    "Method is available for supergroup and channel chats only",
    "Reply message not found"
}

def gkick(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message
    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("You do not seems to be referring to a user")
        return
    user_chat = None
    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message not in GKICK_ERRORS:
            message.reply_text("User cannot be Globally kicked because: {}".format(excp.message))
            return
    except TelegramError:
        pass

    if int(user_id) in DEV_USERS or int(user_id) in DRAGONS:
        message.reply_text("OHHH! Someone's trying to gkick a sudo/support user! *Grabs popcorn*")
        return
    if int(user_id) == OWNER_ID:
        message.reply_text("Wow! Someone's so noob that he want to gkick my owner! *Grabs Potato Chips*")
        return
    if int(user_id) == bot.id:
        message.reply_text("OHH... Let me kick myself.. No way... ")
        return
    chats = get_all_chats()
    name = (
        f"@{user_chat.username}"
        if user_chat and user_chat.username
        else (user_chat.first_name if user_chat else str(user_id))
    )
    message.reply_text("Globally kicking user {}".format(name))
    kicked = 0
    for chat in chats:
        try:
            bot.unban_chat_member(chat.chat_id, user_id)  # Unban_member = kick (and not ban)
            kicked += 1
        except BadRequest as excp:
            if excp.message not in GKICK_ERRORS:
                message.reply_text("User cannot be Globally kicked because: {}".format(excp.message))
                return
        except TelegramError:
            pass
    message.reply_text(f"Done! Kicked from {kicked} chats.")


GKICK_HANDLER = CommandHandler(
    "gkick",
    gkick,
    filters=CustomFilters.sudo_filter | CustomFilters.support_filter,
    run_async=True,
)
dispatcher.add_handler(GKICK_HANDLER)                              
