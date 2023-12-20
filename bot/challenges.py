import logging
from telegram import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update,
    InputMediaPhoto,
)
from telegram.ext import ContextTypes, ConversationHandler
from apscheduler.jobstores.base import JobLookupError

import firebase_util
from utils import send_challenges, challenge_type_to_conv_state, send_step
from constants import Role, ConvState, ChallengeType, MAX_BONUS_GROUPS

logger = logging.getLogger("challenges")


async def submit_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(
        f"@{update.message.from_user.username} attempting to submit a challenge"
    )

    group_info, location, challenge = firebase_util.get_current_challenge(
        update.message.from_user.username
    )

    if group_info.get("race_completed"):
        await update.message.reply_text(
            text=f"Stop wasting time! Just finish up the race and rest!",
        )
        return ConversationHandler.END
    chall_buttons = [
        [InlineKeyboardButton(f"Challenge #{i+1}", callback_data=f"{i}_{location}")]
        for [i, chall] in challenge
    ]
    bonus_idx = firebase_util.has_active_bonus_challenge(
        update.message.from_user.username
    )
    if bonus_idx != None:
        chall_buttons.append(
            [InlineKeyboardButton(f"Bonus", callback_data=f"{bonus_idx}_bonus")]
        )
    await update.message.reply_text(
        text=f"Which challenge do you want to submit?",
        reply_markup=InlineKeyboardMarkup(chall_buttons),
    )
    return ConvState.SelectChallenge


async def skip_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"@{update.message.from_user.username} attempting to SKIP a challenge")

    group_info, location, challenge = firebase_util.get_current_challenge(
        update.message.from_user.username
    )

    if group_info.get("race_completed"):
        await update.message.reply_text(
            text=f"Stop wasting time! Just finish up the race and rest!",
        )
        return ConversationHandler.END
    await update.message.reply_text(
        text=f"Which challenge do you want to skip?",
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
    return ConvState.SelectSkipChallenge


async def select_skip_challenge(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    chall_num, chall_loc = query.data.split("_", 1)
    chall_num = int(chall_num)

    logger.info(
        f"@{query.from_user.username} attempting to SKIP a challenge: {chall_loc} #{chall_num+ 1}"
    )

    await query.edit_message_text(
        text=f"Are you sure you want to skip Challenge #{chall_num + 1} for 100 points?",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Yes", callback_data=query.data)],
                [InlineKeyboardButton("No", callback_data="cancel")],
            ]
        ),
    )

    return ConvState.ConfirmSkip


async def confirm_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text(text=f"Skip cancelled", reply_markup=None)
        return ConversationHandler.END

    chall_num, chall_loc = query.data.split("_", 1)
    chall_num = int(chall_num)

    challs_left = firebase_util.skip_challenge(
        query.from_user.username,
        chall_loc,
        chall_num,
    )

    logger.info(
        f"@{query.from_user.username} SKIPPED a challenge: {chall_loc} #{chall_num+1}"
    )

    await query.edit_message_text(
        text=f"{chall_loc} Challenge #{chall_num+1} skipped", reply_markup=None
    )

    return await post_complete_challenge(challs_left, query.from_user.username, context)


async def select_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    chall_num, chall_loc = query.data.split("_", 1)
    chall_num = int(chall_num)
    context.user_data.update(
        {
            "challenge_number": chall_num,
            "challenge_location": chall_loc,
            "step_number": 0,
            "photos": [],
        }
    )

    step = firebase_util.get_current_step(chall_loc, chall_num, 0)
    step_type = ChallengeType[step["type"]]

    await query.edit_message_text(
        text="Attempting Bonus Challenge"
        if chall_loc == "bonus"
        else f"Attempting Challenge #{chall_num+1}",
        reply_markup=None,
    )

    await send_step(query.from_user.id, context, step)

    logger.info(
        f"@{query.from_user.username} attempting to submit a challenge: {chall_loc} #{chall_num}"
    )

    return challenge_type_to_conv_state(step_type)


async def post_complete_challenge(
    challs_left: int, username: str, context: ContextTypes.DEFAULT_TYPE
):
    if challs_left <= 0:
        group_info, loc, challenge = firebase_util.next_location(username)
        if not challenge:
            await context.bot.send_message(
                group_info["broadcast_channel"],
                "Head back to the endpoint! GO GO GO! The treasure awaits you!",
            )
            return ConversationHandler.END

        await send_challenges(
            context.bot,
            group_info.get("broadcast_channel"),
            loc,
            challenge,
        )
        return ConversationHandler.END

    return ConversationHandler.END


async def process_next_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.update({"step_number": context.user_data.get("step_number") + 1})

    step = firebase_util.get_current_step(
        context.user_data.get("challenge_location"),
        context.user_data.get("challenge_number"),
        context.user_data.get("step_number"),
    )

    if step:
        await send_step(update.message.from_user.id, context, step)
        return challenge_type_to_conv_state(ChallengeType[step["type"]])

    challs_left = firebase_util.complete_challenge(
        update.message.from_user.username,
        context.user_data.get("challenge_location"),
        context.user_data.get("challenge_number"),
    )
    await update.message.reply_text("Challenge completed!")
    if context.user_data.get("challenge_location") == "bonus":
        admin_broadcast, admin_broadcast_thread = firebase_util.get_admin_broadcast()
        await context.bot.send_message(
            admin_broadcast,
            f"Bonus challenge update: {firebase_util.get_number_solved_bonus()}/{MAX_BONUS_GROUPS}",
            message_thread_id=admin_broadcast_thread,
        )
    return await post_complete_challenge(
        challs_left, update.message.from_user.username, context
    )


async def submit_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(
        f"@{update.message.from_user.username} submitted text: {update.message.text}"
    )

    step = firebase_util.get_current_step(
        context.user_data.get("challenge_location"),
        context.user_data.get("challenge_number"),
        context.user_data.get("step_number"),
    )

    if step["answer"] != update.message.text.strip():
        await update.message.reply_text("Incorrect answer")
        return ConvState.SubmitText

    return await process_next_step(update, context)


def get_approval_content(
    update: Update, context: ContextTypes.DEFAULT_TYPE, step, approval_id
):
    rotating_job = context.user_data.get("job")
    rotating_content = (
        f"\n - Rotation: {rotating_job.data['filenames'][rotating_job.data['idx']].split('/')[-1]}"
        if rotating_job
        else ""
    )
    return (
        f"Admins! 빨리주세요! Approve @{update.message.from_user.username} submission for {context.user_data.get('challenge_location')} Challenge #{context.user_data.get('challenge_number')} ({step.get('description')}){rotating_content}\n\nRequest ID: {approval_id}",
        InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Approve",
                        callback_data=f"chall|1|{approval_id}|{update.message.from_user.username}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Reject",
                        callback_data=f"chall|0|{approval_id}|{update.message.from_user.username}",
                    )
                ],
            ]
        ),
    )


async def start_approval_process(
    update: Update, context: ContextTypes.DEFAULT_TYPE, loop_conv_state: ConvState
) -> int:
    step = firebase_util.get_current_step(
        context.user_data.get("challenge_location"),
        context.user_data.get("challenge_number"),
        context.user_data.get("step_number"),
    )

    if (
        loop_conv_state == ConvState.SubmitPhoto
        and "num_photo" in step
        and step["num_photo"] > 0
    ):
        context.user_data.update(
            {"photos": context.user_data.get("photos") + [update.message.photo[-1]]}
        )
        photos = context.user_data.get("photos")
        await update.message.reply_text(
            f"{len(photos)}/{step['num_photo']} photos received"
        )
        if len(photos) != step["num_photo"]:
            return ConvState.SubmitPhoto

        approval_id = firebase_util.generate_approval_request()
        APPROVAL_MESSAGE, APPROVAL_MARKUP = get_approval_content(
            update, context, step, approval_id
        )
        admin_broadcast, admin_broadcast_thread = firebase_util.get_admin_broadcast()
        await context.bot.send_media_group(
            admin_broadcast,
            [InputMediaPhoto(p) for p in photos[:-1]],
            message_thread_id=admin_broadcast_thread,
        )
        approver_captioned_msg = await context.bot.send_photo(
            admin_broadcast,
            photos[-1].file_id,
            caption=APPROVAL_MESSAGE,
            reply_markup=APPROVAL_MARKUP,
            message_thread_id=admin_broadcast_thread,
        )
        approver_captioned_msg_fn = approver_captioned_msg.edit_text
    else:
        media_id = (
            update.message.photo[-1].file_id
            if loop_conv_state == ConvState.SubmitPhoto
            else update.message.video.file_id
        )

        send_fn = (
            context.bot.send_photo
            if loop_conv_state == ConvState.SubmitPhoto
            else context.bot.send_video
        )

        approval_id = firebase_util.generate_approval_request()
        APPROVAL_MESSAGE, APPROVAL_MARKUP = get_approval_content(
            update, context, step, approval_id
        )

        admin_broadcast, admin_broadcast_thread = firebase_util.get_admin_broadcast()
        approver_captioned_msg = await send_fn(
            admin_broadcast,
            media_id,
            caption=APPROVAL_MESSAGE,
            reply_markup=APPROVAL_MARKUP,
            message_thread_id=admin_broadcast_thread,
        )
        approver_captioned_msg_fn = approver_captioned_msg.edit_caption

    waiting_msg = await update.message.reply_text(
        f"Waiting for admin approval...\n\nRequest ID: {approval_id}"
    )

    try:
        result, approver = await firebase_util.wait_approval(approval_id, 300)
        if not result:
            await waiting_msg.edit_text(
                f"Waiting for admin approval...\n\n(Request ID: {approval_id})\n\nMan, you got rejected by @{approver}... Try sending another one! :("
            )
            context.user_data.update({"photos": []})
            return loop_conv_state
    except TimeoutError:
        logger.info(f"Approval request {approval_id} timed out")
        await waiting_msg.edit_text(
            f"Waiting for admin approval...\n\n(Request ID: {approval_id})\n\nApproval timed out. Call @jloh02 and ask him to pay attention! Then send it again pls"
        )
        await approver_captioned_msg_fn(
            f"Haizzz, admins not paying attention... Ask @{update.message.from_user.username} to submit it again"
        )
        return loop_conv_state

    job = context.user_data.get("job")
    if job:
        try:
            job.schedule_removal()
        except JobLookupError:
            logger.warn("Unknown job ID:", job.id)
    await waiting_msg.edit_text(
        f"Waiting for admin approval... Approved by @{approver}!"
    )


async def submit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"@{update.message.from_user.username} submitted photo")
    return await start_approval_process(
        update, context, ConvState.SubmitPhoto
    ) or await process_next_step(update, context)


async def submit_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"@{update.message.from_user.username} submitted video")
    return await start_approval_process(
        update, context, ConvState.SubmitVideo
    ) or await process_next_step(update, context)


async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    role = firebase_util.get_role(query.from_user.username)
    if role != Role.Admin and role != Role.GL:  # TODO Remove GLs
        logger.warn(f"Unauthorized approver: @{query.from_user.username} is a {role}")
        return

    type, status, id, gl_username = query.data.split("|")

    if type != "chall":
        return

    await (
        query.message.edit_caption if query.message.caption else query.message.edit_text
    )(
        f"{'Rejected' if status != '1' else 'Approved'} by @{query.from_user.username}\nRequest ID: {id} (@{gl_username})"
    )

    logger.info(
        f"@{query.from_user.username} {'rejected' if status != '1' else 'approved'} request {id} sent by @{gl_username}"
    )
    firebase_util.update_approval(id, status == "1", query.from_user.username)

    return ConversationHandler.END
