import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

import firebase_util
from utils import send_challenges
from constants import Role, ConvState, Direction

logger = logging.getLogger("user_setup")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data.get("role") == Role.Admin:
        firebase_util.register_admin(update.message.from_user.username)
        logger.info(f"Admin @{update.message.from_user.username} registered")
        await update.message.reply_text("Welcome back admin!")
        return ConversationHandler.END

    if context.user_data.get("role") != Role.Unregistered:
        logger.info(f"GL @{update.message.from_user.username} registered")
        await update.message.reply_text("You've already registered!")
        return ConversationHandler.END

    success = firebase_util.register_user(
        update.message.from_user.username, update.message.from_user.id
    )
    if not success:
        logger.info(
            f"Non-GL/Admin user tried to register: @{update.message.from_user.username}"
        )
        await update.message.reply_text(
            "You can't PM this bot! Ask your GL to do it for you!"
        )
        return ConversationHandler.END

    logger.info(f"GL @{update.message.from_user.username} registered")
    await update.message.reply_text("All aboard! You can start using this amazing bot!")
    return ConversationHandler.END


async def config_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    firebase_util.set_broadcast_group(message.from_user.username, message.chat_id)
    await update.message.reply_text("I'll send updates to this group from now on!")
    return ConversationHandler.END


START_RACE_MARKUP = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "Direction A, Toa Payoh First", callback_data=Direction.A1
            )
        ],
        [
            InlineKeyboardButton(
                "Direction A, Toa Payoh Last", callback_data=Direction.A0
            )
        ],
        [
            InlineKeyboardButton(
                "Direction B, Toa Payoh First", callback_data=Direction.B1
            )
        ],
        [
            InlineKeyboardButton(
                "Direction B, Toa Payoh Last", callback_data=Direction.B0
            )
        ],
    ]
)


async def start_race(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if firebase_util.has_race_started(update.message.from_user.username):
        await update.message.reply_text(
            "Your race has already started! Stop wasting time!"
        )
        return ConversationHandler.END
    await update.message.reply_photo(
        open("images/route.png", "rb"),
        "Choose your direction for challenges\n\n/cancel if you have not been authorized to start",
        reply_markup=START_RACE_MARKUP,
    )
    return ConvState.ChooseDirection


async def choose_direction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_caption(
        f"Confirm Direction {query.data[0]}, Toa Payoh {'First' if query.data[1] == '1' else 'Last'}",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Yes", callback_data=query.data)],
                [InlineKeyboardButton("No", callback_data="cancel")],
            ]
        ),
    )
    return ConvState.ChooseDirectionConfirmation


async def confirm_direction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_caption("Start race cancelled", reply_markup=None)
        return ConversationHandler.END

    await query.edit_message_caption(
        f"The race begins!\n\nDirection {query.data[0]}, Toa Payoh {'First' if query.data[1] == '1' else 'Last'}",
        reply_markup=None,
    )

    firebase_util.start_race(query.from_user.username, query.data)
    group_info, loc, challenge = firebase_util.get_current_challenge(
        query.from_user.username
    )

    await context.bot.send_message(
        group_info.get("broadcast_channel"),
        f"Ahoy! The treasure hunt begins!\n\nRoute Chosen: Direction {query.data[0]}, Toa Payoh {'First' if query.data[1] == '1' else 'Last'}",
    )

    await send_challenges(
        context.bot,
        group_info.get("broadcast_channel"),
        loc,
        challenge,
    )

    admin_broadcast, admin_broadcast_thread = firebase_util.get_admin_broadcast()
    await context.bot.send_message(
        admin_broadcast,
        f"{group_info.get('name')} has started the race",
        message_thread_id=admin_broadcast_thread,
    )
    logger.info(
        f"@{query.from_user.username} selected direction for {group_info['name']}: {query.data}"
    )

    return ConversationHandler.END
