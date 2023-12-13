import firebase_util
from constants import Role
from telegram.ext import ContextTypes, ConversationHandler
from telegram import Update
from telegram._utils.types import SCT
from telegram.constants import ChatType


def dm_only_command(callback, quiet=False) -> SCT:
    async def fn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message if update.message else update.edited_message
        if message.chat.type != ChatType.PRIVATE:
            if not quiet:
                await message.reply_text("This command only works in DMs")
            return ConversationHandler.END
        return await callback(update, context)

    return fn


def role_context_command(callback) -> SCT:
    async def fn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message if update.message else update.edited_message
        context.user_data.update(
            {"role": firebase_util.get_role(message.from_user.username)}
        )
        return await callback(update, context)

    return fn


def role_restricted_command(callback, allow: list[Role], quiet=False) -> SCT:
    async def fn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message if update.message else update.edited_message
        if not context.user_data.get("role") in allow:
            if not quiet:
                await message.reply_text("Unauthorized user. Try /start if you have not")
            return ConversationHandler.END
        return await callback(update, context)

    return role_context_command(fn)


def race_started_only_command(callback) -> SCT:
    async def fn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message if update.message else update.edited_message
        if not firebase_util.has_race_started(message.from_user.username):
            await message.reply_text(
                "The race hasn't started! What are you doing? Stop trying to hack me plsss!"
            )
            return ConversationHandler.END
        return await callback(update, context)

    return role_context_command(fn)


def recent_location_command(callback) -> SCT:
    async def fn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not firebase_util.recent_location_update(update.message.from_user.username):
            await update.message.reply_text("Please ensure your location is updated!")
            return ConversationHandler.END
        return await callback(update, context)

    return fn
