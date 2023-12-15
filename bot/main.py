import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import (
    Update,
    Bot,
    BotCommand,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from constants import (
    Role,
    ConvState,
    TELEGRAM_READ_TIMEOUT,
    TELEGRAM_CONCURRENT_UPDATES,
    CONVERSATION_TIMEOUT,
)
import firebase_util
from middleware import (
    dm_only_command,
    role_context_command,
    role_restricted_command,
    race_started_only_command,
    recent_location_command,
)
from user_setup import (
    start,
    start_race,
    config_group,
    choose_direction,
    confirm_direction,
)
from challenges import (
    submit_challenge,
    select_challenge,
    submit_photo,
    submit_text,
    submit_video,
    handle_approval,
)
from misc_commands import end_race

load_dotenv()
firebase_util.init()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)

logger = logging.getLogger("main")


async def location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message if update.message else update.edited_message
    firebase_util.set_location(
        message.from_user.username,
        message.location.latitude,
        message.location.longitude,
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled")
    return ConversationHandler.END


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"@{update.message.from_user.username} resetted the game state")

    firebase_util.reset()
    await update.message.reply_text("Resetted game state")
    return ConversationHandler.END


def main() -> None:
    application = (
        Application.builder()
        .token(os.environ.get("TELEGRAM_BOT_KEY"))
        .read_timeout(TELEGRAM_READ_TIMEOUT)
        .concurrent_updates(TELEGRAM_CONCURRENT_UPDATES)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", dm_only_command(role_context_command(start))),
            CommandHandler(
                "configgroup",
                role_restricted_command(config_group, [Role.GL]),
            ),
            CommandHandler(
                "reset",
                dm_only_command(
                    role_restricted_command(reset, [Role.Admin, Role.GL])
                ),  # TODO change this to admin only
            ),
            CommandHandler(
                "startrace",
                dm_only_command(
                    role_restricted_command(
                        recent_location_command(start_race), [Role.GL]
                    )
                ),
            ),
            CommandHandler(
                "submit",
                dm_only_command(
                    role_restricted_command(
                        race_started_only_command(
                            recent_location_command(submit_challenge)
                        ),
                        [Role.GL],
                    )
                ),
            ),
            CommandHandler(
                "endrace",
                dm_only_command(
                    role_restricted_command(
                        race_started_only_command(recent_location_command(end_race)),
                        [Role.GL],
                    )
                ),
            ),
            MessageHandler(
                filters.LOCATION,
                dm_only_command(
                    role_restricted_command(location, [Role.GL], quiet=True), quiet=True
                ),
            ),
        ],
        states={
            ConvState.ChooseDirection: [CallbackQueryHandler(choose_direction)],
            ConvState.ChooseDirectionConfirmation: [
                CallbackQueryHandler(confirm_direction)
            ],
            ConvState.SelectChallenge: [CallbackQueryHandler(select_challenge)],
            ConvState.SubmitText: [
                CommandHandler("cancel", cancel),
                MessageHandler(filters.TEXT, submit_text),
            ],
            ConvState.SubmitPhoto: [MessageHandler(filters.PHOTO, submit_photo)],
            ConvState.SubmitVideo: [MessageHandler(filters.VIDEO, submit_video)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=CONVERSATION_TIMEOUT,
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_approval, r"chall\|.*"))

    # Run the bot until the user presses Ctrl-C
    if os.environ.get("WEBHOOK_URL"): 
      application.run_webhook(
        listen="0.0.0.0",
        port="8080",
        webhook_url=os.environ.get("WEBHOOK_URL"), 
        allowed_updates=Update.ALL_TYPES
      )
    else:  
      application.run_polling(allowed_updates=Update.ALL_TYPES)
    


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        Bot(os.environ.get("TELEGRAM_BOT_KEY")).set_my_commands(
            [
                BotCommand("start", "Register user"),
                BotCommand("configgroup", "Use current chat for group updates"),
                BotCommand("submit", "Attempt a challenge"),
                BotCommand("startrace", "Start the race (Only when told to do so)"),
                BotCommand(
                    "endrace", "Press at finishing line after challenges completed"
                ),
                BotCommand("cancel", "Cancel the command. Also use when bot hangs"),
            ]
        )
    )
    loop.run_until_complete(main())
