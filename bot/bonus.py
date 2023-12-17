import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

import firebase_util
from constants import ConvState, MAX_BONUS_GROUPS

logger = logging.getLogger("bonus")


async def start_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Confirm sending next bonus challenge",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Yes", callback_data="yes")],
                [InlineKeyboardButton("No", callback_data="no")],
            ]
        ),
    )
    return ConvState.ConfirmBonus


async def confirm_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data != "yes":
        await query.message.edit_text("Bonus challenge cancelled")
        return ConversationHandler.END

    desc = firebase_util.get_current_bonus_challenge().get("description")
    await query.message.edit_text("Sending next bonus challenge")
    for chat in firebase_util.get_all_group_broadcast():
        await context.bot.send_message(
            chat,
            f"A new challenge awaits! Only the first {MAX_BONUS_GROUPS} groups get points for it! Hurry and complete it!\n\n{desc}\n\n/submit and choose Bonus",
        )

    return ConversationHandler.END
