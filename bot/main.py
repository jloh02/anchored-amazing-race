from dotenv import load_dotenv
import os
import firebase_util
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

load_dotenv()

firebase_util.init()
firebase_util.read()


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!"
    )


if __name__ == "__main__":
    application = ApplicationBuilder().token(os.environ.get("TELEGRAM_BOT_KEY")).build()

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    application.run_polling()
