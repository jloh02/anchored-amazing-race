import logging
from geopy import distance
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

import firebase_util
from constants import END_LAT_LNG, END_TOLERANCE

logger = logging.getLogger("misc")


async def end_race(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not firebase_util.has_race_ended(update.message.from_user.username):
        await update.message.reply_text("Finish your challenges first!")
        return ConversationHandler.END
    logger.info(f"@{update.message.from_user.username} ending race")
    location = firebase_util.get_location(update.message.from_user.username)
    if not location:
        await update.message.reply_text(
            "Location not found, please make sure your location is on"
        )
        return ConversationHandler.END

    d = distance.geodesic((location.latitude, location.longitude), END_LAT_LNG).m
    logger.info(f"@{update.message.from_user.username} distance from endpoint: {d}m")
    if d > END_TOLERANCE:
        await update.message.reply_text("You're too far from the endpoint!")
        return ConversationHandler.END

    start_time, end_time = firebase_util.end_race(update.message.from_user.username)
    duration_in_s = (end_time - start_time).total_seconds()
    logger.info(
        f"@{update.message.from_user.username} finished race at {end_time} (Duration: {duration_in_s} seconds)"
    )
    hours_tup = divmod(duration_in_s, 3600)
    mins_tup = divmod(hours_tup[1], 60)
    await update.message.reply_text(
        f"Congrats! You have finished the race!\n\nTotal time: {int(hours_tup[0])}h {int(mins_tup[0])}min {int(mins_tup[1])}s"
    )
    return ConversationHandler.END
