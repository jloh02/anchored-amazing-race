import os
import random
import subprocess
import platform
from functools import reduce
from telegram import Bot, InputMediaPhoto
from telegram.ext import ContextTypes
from constants import ConvState, ChallengeType, PHOTO_ROTATION_TIME


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


async def send_step(chat_id: id, context: ContextTypes.DEFAULT_TYPE, step):
    if "rotating_media" in step:
        dir = "images/" + step["rotating_media"] + "/"
        filenames = list(map(lambda x: dir + x, os.listdir(dir)))
        files = list(
            map(
                lambda x: InputMediaPhoto(open(x, "rb"), caption=step["description"]),
                filenames,
            )
        )
        start_idx = random.randint(0, len(filenames) - 1)

        msg = await context.bot.send_photo(
            chat_id, open(filenames[start_idx], "rb"), caption=step["description"]
        )
        job = None

        async def rotate_photo(ctx: ContextTypes.DEFAULT_TYPE):
            ctx.job.data["idx"] += 1
            if ctx.job.data["idx"] >= len(files):
                ctx.job.data["idx"] = 0
            await msg.edit_media(files[ctx.job.data["idx"]])

        job = context.job_queue.run_repeating(
            rotate_photo,
            PHOTO_ROTATION_TIME,
            data={"idx": start_idx, "filenames": filenames},
        )
        context.user_data.update({"job": job})

    elif "media" in step:
        await context.bot.send_photo(
            chat_id,
            open("images/" + step["media"], "rb"),
            caption=step["description"],
        )
    else:
        await context.bot.send_message(chat_id, step["description"])


def challenge_type_to_conv_state(chall_type: ChallengeType):
    if chall_type == ChallengeType.Text:
        return ConvState.SubmitText
    elif chall_type == ChallengeType.Video:
        return ConvState.SubmitVideo
    elif chall_type == ChallengeType.Photo:
        return ConvState.SubmitPhoto


def get_logs(err: bool):
    try:
        result = subprocess.run(
            [
                "pm2",
                "logs",
                "bot",
                ("--err" if err else "--out"),
                "--nostream",
                "--raw",
                "--lines",
                "100",
            ],
            capture_output=True,
            text=True,
            shell=platform.system() != "Linux",
        )

        if result.returncode == 0:
            return result.stdout + result.stderr
        else:
            return f"Error reading logs: {result.stderr}"

    except Exception as e:
        print(f"An error occurred: {e}")

    return "Error"
