import requests
from IronRobo import CASH_API_KEY, dispatcher
from telegram import ParseMode, Update
from telegram.ext import CallbackContext, CommandHandler

USAGE = (
    "*Currency converter:*\n"
    "`/cash <amount> <from> <to>`\n"
    "Example: `/cash 1 USD INR`"
)


def get_rate(orig_cur, new_cur):
    """Exchange rate from orig_cur to new_cur, or None if unknown."""
    if CASH_API_KEY:
        try:
            response = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "CURRENCY_EXCHANGE_RATE",
                    "from_currency": orig_cur,
                    "to_currency": new_cur,
                    "apikey": CASH_API_KEY,
                },
                timeout=15,
            ).json()
            return float(response["Realtime Currency Exchange Rate"]["5. Exchange Rate"])
        except (requests.RequestException, KeyError, ValueError):
            pass
    # Free, keyless daily rates.
    data = requests.get(f"https://open.er-api.com/v6/latest/{orig_cur}", timeout=15).json()
    if data.get("result") != "success":
        return None
    return data.get("rates", {}).get(new_cur)


def convert(update: Update, context: CallbackContext):
    args = update.effective_message.text.split()

    if len(args) == 4:
        try:
            orig_cur_amount = float(args[1])
        except ValueError:
            update.effective_message.reply_text("Invalid Amount Of Currency")
            return

        orig_cur = args[2].upper()
        new_cur = args[3].upper()
        try:
            current_rate = get_rate(orig_cur, new_cur)
        except (requests.RequestException, ValueError):
            update.effective_message.reply_text("The exchange rate service isn't reachable, try again later.")
            return
        if current_rate is None:
            update.effective_message.reply_text("Currency Not Supported.")
            return
        new_cur_amount = round(orig_cur_amount * current_rate, 5)
        update.effective_message.reply_text(
            f"{orig_cur_amount} {orig_cur} = {new_cur_amount} {new_cur}"
        )

    elif len(args) == 1:
        update.effective_message.reply_text(USAGE, parse_mode=ParseMode.MARKDOWN)

    else:
        update.effective_message.reply_text(
            f"*Invalid Args!!:* Required 3 But Passed {len(args) -1}\n\n{USAGE}",
            parse_mode=ParseMode.MARKDOWN,
        )


CONVERTER_HANDLER = CommandHandler("cash", convert, run_async=True)

dispatcher.add_handler(CONVERTER_HANDLER)

__command_list__ = ["cash"]
__handlers__ = [CONVERTER_HANDLER]
