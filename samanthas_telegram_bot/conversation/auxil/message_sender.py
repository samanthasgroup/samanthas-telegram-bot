# This module contains some send_message operations that are too complex to be included in the main
# code, and at the same time need to run multiple times.
import datetime
from contextlib import suppress

import telegram.error
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode

from samanthas_telegram_bot.conversation.data_structures.constants import Locale
from samanthas_telegram_bot.conversation.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.conversation.data_structures.enums import (
    CommonCallbackData,
    ConversationMode,
    Role,
)


class MessageSender:
    """A helper class that sends replies to user by executing
    `update.effective_chat.send_message()`.

    Methods in this class are called several times in the bot's code and/or are complex.

    All methods in this class are **static methods**. This is a class is just a namespace
    and a way to be stylistically consistent with other helper classes.
    """

    @staticmethod
    async def ask_phone_number(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
        """Sends a message to ask for phone number."""
        locale: Locale = context.user_data.locale

        await update.effective_chat.send_message(
            context.bot_data.phrases["ask_phone"][locale],
            disable_web_page_preview=True,  # the message contains link to site with country codes
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardMarkup(
                [
                    [
                        KeyboardButton(
                            text=context.bot_data.phrases["share_phone"][locale],
                            request_contact=True,
                        )
                    ]
                ]
            ),
        )

    @classmethod
    async def ask_review(cls, update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
        """Sends a message to the user for them to review their basic info."""

        # If there was no message immediately before the review message is sent to user,
        # attempt to delete it will cause BadRequest.
        # This is fine: we want to delete a message if it exists.
        with suppress(telegram.error.BadRequest):
            await update.effective_message.delete()  # remove whatever was before the review

        data = context.user_data
        locale: Locale = data.locale

        if data.role == Role.TEACHER and context.chat_data.mode == ConversationMode.NORMAL:
            data.teacher_additional_skills_comment = update.message.text

        buttons = [
            InlineKeyboardButton(
                text=context.bot_data.phrases["review_reaction_" + option][locale],
                callback_data=option,
            )
            for option in ("yes", "no")
        ]

        await update.effective_chat.send_message(
            text=cls._prepare_message_for_review(update, context),
            # each button in a separate list to make them show in one column
            reply_markup=InlineKeyboardMarkup([[buttons[0]], [buttons[1]]]),
        )

    @staticmethod
    async def ask_store_username(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
        """Asks if user's Telegram username should be stored or they want to give phone number."""
        locale: Locale = context.user_data.locale
        username = update.effective_user.username

        await update.effective_chat.send_message(
            f"{context.bot_data.phrases['ask_username_1'][locale]} @{username}"
            f"{context.bot_data.phrases['ask_username_2'][locale]}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=context.bot_data.phrases[f"username_reply_{option}"][locale],
                            callback_data=f"store_username_{option}",
                        )
                        for option in (CommonCallbackData.YES, CommonCallbackData.NO)
                    ],
                ]
            ),
        )

    @staticmethod
    def _prepare_message_for_review(update: Update, context: CUSTOM_CONTEXT_TYPES) -> str:
        """Prepares text message with user info for review, depending on role and other factors."""
        data = context.user_data
        locale: Locale = data.locale

        message = (
            f"{context.bot_data.phrases['ask_review'][locale]}\n\n"
            f"{context.bot_data.phrases['review_first_name'][locale]}: {data.first_name}\n"
            f"{context.bot_data.phrases['review_last_name'][locale]}: {data.last_name}\n"
            f"{context.bot_data.phrases['review_email'][locale]}: {data.email}\n"
        )

        if data.role == Role.STUDENT:
            message += (
                f"{context.bot_data.phrases['review_student_age_group'][locale]}: "
                f"{data.student_age_from}-{data.student_age_to}\n"
            )

        if data.tg_username:
            message += (
                f"{context.bot_data.phrases['review_username'][locale]} (@{data.tg_username})\n"
            )
        if data.phone_number:
            message += (
                f"{context.bot_data.phrases['review_phone_number'][locale]}: {data.phone_number}\n"
            )

        offset_hour = data.utc_offset_hour
        offset_minute = str(data.utc_offset_minute).zfill(2)  # to produce "00" from 0

        if data.utc_offset_hour > 0:
            message += f"{context.bot_data.phrases['review_timezone'][locale]}: UTC+{offset_hour}"
        elif data.utc_offset_hour < 0:
            message += f"{context.bot_data.phrases['review_timezone'][locale]}: UTC{offset_hour}"
        else:
            message += f"\n{context.bot_data.phrases['review_timezone'][locale]}: UTC"

        utc_time = update.effective_message.date
        now_with_offset = utc_time + datetime.timedelta(
            hours=data.utc_offset_hour, minutes=data.utc_offset_minute
        )
        message += (
            f" ({context.bot_data.phrases['current_time'][locale]} "
            f"{now_with_offset.strftime('%H:%M')})\n"
        )

        message += f"\n{context.bot_data.phrases['review_availability'][locale]}:\n"
        # The dictionary of days contains keys for all days of week. Only display the days to the
        # user that they have chosen slots for:
        for idx, day in enumerate(data.time_slots_for_day):
            slots = data.time_slots_for_day[day]
            if slots:
                message += f"{context.bot_data.phrases['ask_slots_' + str(idx)][locale]}: "
            # sort by first part of slot as a number (otherwise "8:00" will be after "11:00")
            for slot in sorted(slots, key=lambda s: int(s.split("-")[0])):
                # user must see their slots in their chosen timezone
                hour_from, hour_to = slot.split("-")

                # % 24 is needed to avoid showing 22:00-25:00 to the user
                message += (
                    f" {(int(hour_from) + offset_hour) % 24}:{offset_minute}-"
                    f"{(int(hour_to) + offset_hour) % 24}:{offset_minute};"
                )
            else:  # remove last semicolon, end day with line break
                message = message[:-1] + "\n"
        message += "\n"

        # Because of complex logic around English, we will not offer the student to review their
        # language/level for now.  This option will be reserved for teachers.
        if data.role == Role.TEACHER:
            message += f"{context.bot_data.phrases['review_languages_levels'][locale]}:\n"
            for language in data.levels_for_teaching_language:
                message += f"{context.bot_data.phrases[language][locale]}: "
                message += ", ".join(sorted(data.levels_for_teaching_language[language])) + "\n"
            message += "\n"

        message += f"{context.bot_data.phrases['review_communication_language'][locale]}: "
        message += (
            context.bot_data.phrases[
                f"class_communication_language_option_{data.communication_language_in_class}"
            ][locale]
            + "\n"
        )

        return message
