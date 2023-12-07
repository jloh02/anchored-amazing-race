from dotenv import load_dotenv
import os
import firebase_util
import logging
from constants import Role, ConvState
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram._utils.types import SCT
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

    firebase_util.register_user(update.message.from_user.username)
    await update.message.reply_text("All aboard! You can start using this amazing bot!")
    return ConversationHandler.END


async def location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END


def dm_only_command(callback) -> SCT:
    async def fn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if update.message.chat_id != update.message.from_user.id:
            await update.message.reply_text("This command only works in DM")
            return ConversationHandler.END
        return await callback(update, context)

    return fn


def role_context_command(callback) -> SCT:
    async def fn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["role"] = firebase_util.get_role(
            update.message.from_user.username
        )
        return await callback(update, context)

    return fn


def role_restricted_command(callback, allow: list[Role]) -> SCT:
    async def fn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not context.user_data["role"] in allow:
            await update.message.reply_text("Unauthorized User")
            return ConversationHandler.END
        return await callback(update, context)

    return role_context_command(fn)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled")
    return ConversationHandler.END


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    firebase_util.reset()
    await update.message.reply_text("Resetting game state")
    return ConversationHandler.END


def main() -> None:
    application = (
        Application.builder().token(os.environ.get("TELEGRAM_BOT_KEY")).build()
    )

    MENU_DICT = {}

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", dm_only_command(role_context_command(start))),
            MessageHandler(
                filters.LOCATION, role_restricted_command(location, [Role.GL])
            ),
            CommandHandler("reset", role_restricted_command(reset, [Role.Admin])),
        ],
        states={
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
