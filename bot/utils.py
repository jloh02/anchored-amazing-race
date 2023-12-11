from functools import reduce
from telegram import Bot


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
