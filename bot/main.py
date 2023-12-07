from dotenv import load_dotenv
import os
import firebase_util
import logging
from constants import Role, ConvState, Direction
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram._utils.types import SCT
from telegram.constants import ChatType
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

load_dotenv()

firebase_util.init()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data["role"] == Role.Admin:
        firebase_util.register_admin(update.message.from_user.username)
        await update.message.reply_text(
            "All aboard! You can start using this amazing bot!"
        )
        return ConversationHandler.END

    if context.user_data["role"] != Role.Unregistered:
        await update.message.reply_text("You've already registered!")
        return ConversationHandler.END

    firebase_util.register_user(
        update.message.from_user.username, update.message.from_user.id
    )
    await update.message.reply_text("All aboard! You can start using this amazing bot!")
    return ConversationHandler.END


async def location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message if update.message else update.edited_message
    firebase_util.set_location(
        message.from_user.username,
        message.location.latitude,
        message.location.longitude,
    )
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


async def config_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    firebase_util.set_broadcast_group(message.from_user.username, message.chat_id)
    await update.message.reply_text("I'll send updates to this group now!")
    return ConversationHandler.END


async def start_race(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not firebase_util.recent_location_update(update.message.from_user.username):
        await update.message.reply_text("Please ensure your location is updated!")
        return ConversationHandler.END
    await update.message.reply_text(
        "Choose your direction for challenges\n\n/cancel if you have not been authorized to start",
        reply_markup=START_RACE_MARKUP,
    )
    return ConvState.ChooseDirection


async def choose_direction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text=f"Confirm Direction {query.data[0]}, Toa Payoh {'First' if query.data[1] == '1' else 'Last'}",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Yes", callback_data=query.data)],
                [InlineKeyboardButton("No", callback_data="cancel")],
            ]
        ),
    )
    return ConvState.ChooseDirectionConfirmation


async def confirm_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Start race cancelled", reply_markup=None)
        return ConversationHandler.END

    await query.edit_message_text(
        text=f"The hunt begins!\n\nDirection {query.data[0]}, Toa Payoh {'First' if query.data[1] else 'Last'}",
        reply_markup=None,
    )
    firebase_util.start_race(query.from_user.username, query.data)
    return ConversationHandler.END


def dm_only_command(callback, quiet=False) -> SCT:
    async def fn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message if update.message else update.edited_message
        if message.chat.type != ChatType.PRIVATE:
            if not quiet:
                await message.reply_text("This command only works in DMs")
            return ConversationHandler.END
        return await callback(update, context)

    return fn


def role_context_command(callback) -> SCT:
    async def fn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message if update.message else update.edited_message
        context.user_data["role"] = firebase_util.get_role(message.from_user.username)
        return await callback(update, context)

    return fn


def role_restricted_command(callback, allow: list[Role], quiet=False) -> SCT:
    async def fn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message if update.message else update.edited_message
        if not context.user_data["role"] in allow:
            if not quiet:
                await message.reply_text("Unauthorized User")
            return ConversationHandler.END
        return await callback(update, context)

    return role_context_command(fn)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled")
    return ConversationHandler.END


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    firebase_util.reset()
    await update.message.reply_text("Resetted game state")
    return ConversationHandler.END


def main() -> None:
    application = (
        Application.builder().token(os.environ.get("TELEGRAM_BOT_KEY")).build()
    )

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", dm_only_command(role_context_command(start))),
            CommandHandler(
                "configgroup", role_restricted_command(config_group, [Role.GL])
            ),
            MessageHandler(
                filters.LOCATION,
                dm_only_command(
                    role_restricted_command(location, [Role.GL], quiet=True), quiet=True
                ),
            ),
            CommandHandler(
                "reset", dm_only_command(role_restricted_command(reset, [Role.Admin]))
            ),
            CommandHandler(
                "startrace",
                dm_only_command(role_restricted_command(start_race, [Role.GL])),
            ),
            CommandHandler,
        ],
        states={
            ConvState.ChooseDirection: [CallbackQueryHandler(choose_direction)],
            ConvState.ChooseDirectionConfirmation: [
                CallbackQueryHandler(confirm_location)
            ],
            # ConvState.Menu: [
            #     CallbackQueryHandler(fn, pattern=f"^{cmd}$")
            #     for cmd, fn in MENU_DICT.items()
            # ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
