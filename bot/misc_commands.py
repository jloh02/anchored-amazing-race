import logging
from io import BytesIO
from geopy import distance
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from telegram import Update, InputFile
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

import firebase_util
from constants import Direction, END_LAT_LNG, END_TOLERANCE, NUMBER_LOCATIONS
from utils import get_start_chall_index

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


def get_progress(group: dict) -> int:
    if (
        not "start_time" in group
        or not "direction" in group
        or not "current_location" in group
    ):
        return -1
    if group.get("race_completed"):
        return NUMBER_LOCATIONS + 1
    if group.get("end_time"):
        return NUMBER_LOCATIONS + 2
    return (
        (
            group.get("current_location")
            - get_start_chall_index(Direction[group.get("direction")])
        )
        * (-1 if group.get("direction")[0] == "B" else 1)
        + (NUMBER_LOCATIONS + 1)
    ) % (NUMBER_LOCATIONS + 1)


def get_progress_str(group: dict) -> int:
    prog = get_progress(group)

    if prog == -1:
        return "Have not started"
    if prog == NUMBER_LOCATIONS + 2:
        return "Finished race"
    return f"{prog} locations finished"


def get_progress_str_with_name(group: dict) -> int:
    return [group.get("name"), get_progress_str(group)]


def create_table(data):
    fig, ax = plt.subplots(figsize=(10, 10))
    # ax.axis("tight")
    table = ax.table(
        cellText=data,
        colLabels=["Group", "Status"],
        cellLoc="center",
        loc="center",
        bbox=[0, 0, 1, 1],
    )
    fig.tight_layout()

    for (row, col), cell in table.get_celld().items():
        cell.PAD = 0.5
        if (row == 0) or (col == -1):
            cell.set_text_props(fontproperties=FontProperties(weight="bold"))

    ax.axis("off")
    table.auto_set_font_size(False)
    table.set_fontsize(14)
    table.auto_set_column_width(col=list(range(2)))

    # Save the table as an image in memory
    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close()

    return buffer


async def get_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    groups = firebase_util.get_all_group_status()

    await update.message.reply_photo(
        InputFile(create_table(list(map(get_progress_str_with_name, groups))))
    )
    return ConversationHandler.END
