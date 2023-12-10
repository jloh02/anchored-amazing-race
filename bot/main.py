import os
import logging
from functools import reduce
from dotenv import load_dotenv
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update, Bot
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from constants import Role, ConvState, Direction, ChallengeType
import firebase_util
from middleware import (
    dm_only_command,
    role_context_command,
    role_restricted_command,
    race_started_only_command,
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

bot = Bot(os.environ.get("TELEGRAM_BOT_KEY"))
bot.set_my_commands(
    ["start", "Register user"],
    ["configgroup", "Use current chat for group updates"],
    ["startrace", "Start the race (Only when told to do so)"],
    ["submit", "Attempt a challenge"],
    ["endrace", "Only press at finish line"],
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data["role"] == Role.Admin:
        firebase_util.register_admin(update.message.from_user.username)
        await update.message.reply_text("Welcome back admin!")
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
    if firebase_util.has_race_started(update.message.from_user.username):
        await update.message.reply_text(
            "Your race has already started! Stop wasting time!"
        )
        return ConversationHandler.END
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


async def send_challenges(bot: Bot, chat_id: int, loc: str, challenges):
    await bot.send_message(
        chat_id,
        reduce(
            lambda acc, iv: acc
            + (f"Challenge #{iv[0]+1}:\n{iv[1]['description']}\n\n" if iv[1] else ""),
            challenges,
            f"Challenges for {loc}\n---------------------------------------------\n",
        ),
    )


async def confirm_direction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Start race cancelled", reply_markup=None)
        return ConversationHandler.END

    await query.edit_message_text(
        text=f"The race begins!\n\nDirection {query.data[0]}, Toa Payoh {'First' if query.data[1] == '1' else 'Last'}",
        reply_markup=None,
    )

    firebase_util.start_race(query.from_user.username, query.data)
    group_info, loc, challenge = firebase_util.get_current_challenge(
        query.from_user.username
    )

    await context.bot.send_message(
        group_info["broadcast_channel"],
        f"Ahoy! The treasure hunt begins!\n\nRoute Chosen: Direction {query.data[0]}, Toa Payoh {'First' if query.data[1] == '1' else 'Last'}",
    )

    await send_challenges(
        context.bot,
        group_info["broadcast_channel"],
        loc,
        challenge,
    )

    await context.bot.send_message(
        firebase_util.get_admin_broadcast(),
        f"{group_info['name']} has started the race",
    )
    logger.info(
        f"@{query.from_user.username} selected direction for {group_info['name']}: {query.data}"
    )

    return ConversationHandler.END


async def submit_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(
        f"@{update.message.from_user.username} attempting to submit a challenge"
    )

    group_info, location, challenge = firebase_util.get_current_challenge(
        update.message.from_user.username
    )
    await update.message.reply_text(
        text=f"Which challenge do you want to submit?",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"Challenge #{i+1}", callback_data=f"{i}_{location}"
                    )
                ]
                for [i, chall] in challenge
            ]
        ),
    )
    return ConvState.SelectChallenge


def challenge_type_to_conv_state(chall_type: ChallengeType):
    if chall_type == ChallengeType.Text:
        return ConvState.SubmitText
    elif chall_type == ChallengeType.Video:
        return ConvState.SubmitVideo
    elif chall_type == ChallengeType.Photo:
        return ConvState.SubmitPhoto


async def select_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    chall_num, chall_loc = query.data.split("_", 1)
    chall_num = int(chall_num)
    context.user_data["challenge_number"], context.user_data["challenge_location"] = (
        chall_num,
        chall_loc,
    )
    context.user_data["step_number"] = 0

    step = firebase_util.get_current_step(chall_loc, chall_num, 0)
    context.user_data["waiting_messages"] = step["num_messages"]
    chall_type = ChallengeType[step["type"]]

    await query.edit_message_text(
        text=step["description"],
        reply_markup=None,
    )

    return challenge_type_to_conv_state(chall_type)


async def process_next_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["step_number"] += 1

    step = firebase_util.get_current_step(
        context.user_data["challenge_location"],
        context.user_data["challenge_number"],
        context.user_data["step_number"],
    )

    if step:
        await update.message.reply_text(step["description"])
        return challenge_type_to_conv_state(ChallengeType[step["type"]])

    challs_left = firebase_util.complete_challenge(
        update.message.from_user.username,
        context.user_data["challenge_location"],
        context.user_data["challenge_number"],
    )
    await update.message.reply_text("Challenge completed!")

    if challs_left <= 0:
        group_info, loc, challenge = firebase_util.next_location(
            update.message.from_user.username
        )
        if not challenge:
            await context.bot.send_message(
                group_info["broadcast_channel"],
                "Head back to the endpoint! GO GO GO! The treasure awaits you!",
            )
            return ConversationHandler.END

        await send_challenges(
            context.bot,
            group_info["broadcast_channel"],
            loc,
            challenge,
        )
        return ConversationHandler.END

    await update.message.reply_text("Challenge completed")

    return ConversationHandler.END


async def submit_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(
        f"@{update.message.from_user.username} submitted text: {update.message.text}"
    )

    step = firebase_util.get_current_step(
        context.user_data["challenge_location"],
        context.user_data["challenge_number"],
        context.user_data["step_number"],
    )

    if step["answer"] != update.message.text.strip():
        await update.message.reply_text("Incorrect answer")
        return ConvState.SubmitText

    return await process_next_step(update, context)


async def submit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"@{update.message.from_user.username} submitted photo")

    await context.bot.send_photo(
        firebase_util.get_admin_broadcast(),
        update.message.photo[-1]["file_id"],
        f"Photo from @{update.message.from_user.username}",
    )
    return await process_next_step(update, context)


async def submit_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"@{update.message.from_user.username} submitted video")

    await context.bot.send_video(
        firebase_util.get_admin_broadcast(),
        update.message.video.file_id,
        f"Photo from @{update.message.from_user.username}",
    )
    return await process_next_step(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled")
    return ConversationHandler.END


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"@{update.message.from_user.username} resetted the game state")

    firebase_util.reset()
    await update.message.reply_text("Resetted game state")
    return ConversationHandler.END


COMMANDS = []


def main() -> None:
    application = (
        Application.builder().token(os.environ.get("TELEGRAM_BOT_KEY")).build()
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
                dm_only_command(role_restricted_command(start_race, [Role.GL])),
            ),
            CommandHandler(
                "submit",
                dm_only_command(
                    role_restricted_command(
                        race_started_only_command(submit_challenge), [Role.GL]
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
            ConvState.SubmitText: [MessageHandler(filters.TEXT, submit_text)],
            ConvState.SubmitPhoto: [MessageHandler(filters.PHOTO, submit_photo)],
            ConvState.SubmitVideo: [MessageHandler(filters.VIDEO, submit_video)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
