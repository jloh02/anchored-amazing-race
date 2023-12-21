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

import uvicorn
from http import HTTPStatus
from flask_cors import CORS
from asgiref.wsgi import WsgiToAsgi
from flask import Flask, Response, make_response, request

from constants import (
    Role,
    ConvState,
    TELEGRAM_READ_TIMEOUT,
    TELEGRAM_WRITE_TIMEOUT,
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
    skip_challenge,
    select_skip_challenge,
    confirm_skip,
    submit_photo,
    submit_text,
    submit_video,
    handle_approval,
)
from bonus import start_bonus, confirm_bonus
from misc_commands import end_race, get_status
from utils import get_logs

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

    admin_broadcast, admin_broadcast_thread = firebase_util.get_admin_broadcast()

    firebase_util.reset()
    await update.message.reply_text("Resetted game state")
    await context.bot.send_message(
        admin_broadcast,
        f"@{update.message.from_user.username} resetted game state",
        message_thread_id=admin_broadcast_thread,
    )
    return ConversationHandler.END


async def main() -> None:
    application = (
        Application.builder()
        .token(os.environ.get("TELEGRAM_BOT_KEY"))
        .read_timeout(TELEGRAM_READ_TIMEOUT)
        .write_timeout(TELEGRAM_WRITE_TIMEOUT)
        .concurrent_updates(TELEGRAM_CONCURRENT_UPDATES)
        .build()
    )

    await Bot(os.environ.get("TELEGRAM_BOT_KEY")).set_my_commands(
        [
            BotCommand("start", "Register user"),
            BotCommand("configgroup", "Use current chat for group updates"),
            BotCommand("submit", "Attempt a challenge"),
            BotCommand("skip", "Skip a challenge"),
            BotCommand("status", "Find out where other groups are"),
            BotCommand("startrace", "Start the race (Only when told to do so)"),
            BotCommand("endrace", "Press at finishing line after challenges completed"),
            BotCommand("cancel", "Cancel the command. Also use when bot hangs"),
        ]
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
                ),  # TODO remove this during game
            ),
            CommandHandler("status", get_status),
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
            CommandHandler(
                "skip",
                dm_only_command(
                    role_restricted_command(
                        skip_challenge,
                        [Role.GL],
                    )
                ),
            ),
            CommandHandler(
                "nextbonus",
                dm_only_command(
                    role_restricted_command(
                        start_bonus,
                        [Role.GL, Role.Admin],  # TODO change this to admin only
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
            ConvState.ConfirmBonus: [CallbackQueryHandler(confirm_bonus)],
            ConvState.SelectSkipChallenge: [
                CallbackQueryHandler(select_skip_challenge)
            ],
            ConvState.ConfirmSkip: [CallbackQueryHandler(confirm_skip)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=CONVERSATION_TIMEOUT,
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_approval, r"chall\|.*"))

    flask_app = Flask(__name__)

    @flask_app.post("/telegram")
    async def telegram() -> Response:
        await application.update_queue.put(
            Update.de_json(data=request.json, bot=application.bot)
        )
        return Response(status=HTTPStatus.OK)

    @flask_app.get("/ping")
    async def ping() -> Response:
        response = make_response("pong", HTTPStatus.OK)
        response.mimetype = "text/plain"
        return response

    @flask_app.get("/logs/err")
    async def logs_err() -> Response:
        response = make_response(get_logs(True), HTTPStatus.OK)
        response.mimetype = "text/plain"
        return response

    @flask_app.get("/logs/out")
    async def logs_out() -> Response:
        response = make_response(get_logs(False), HTTPStatus.OK)
        response.mimetype = "text/plain"
        return response

    if os.environ.get("WEBHOOK_URL"):
        webserver = uvicorn.Server(
            config=uvicorn.Config(
                app=WsgiToAsgi(flask_app),
                port=8080,
                use_colors=False,
                host="0.0.0.0",
            )
        )

        await application.bot.set_webhook(
            url=f"{os.environ.get('WEBHOOK_URL')}/telegram",
            allowed_updates=Update.ALL_TYPES,
        )
        async with application:
            await application.initialize()
            await application.start()
            await webserver.serve()
            await application.stop()
            await application.shutdown()

    else:
        webserver = uvicorn.Server(
            config=uvicorn.Config(
                app=WsgiToAsgi(flask_app),
                port=8080,
                use_colors=False,
                host="127.0.0.1",
            )
        )
        CORS(flask_app)

        async with application:
            await application.initialize()
            await application.start()
            await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            await webserver.serve()
            await application.updater.stop()
            await application.stop()
            await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
