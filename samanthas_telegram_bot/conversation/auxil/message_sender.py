# This module contains some send_message operations that are too complex to be included in the main
# code, and at the same time need to run multiple times.
import datetime
from collections import defaultdict
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

from samanthas_telegram_bot.conversation.auxil.enums import CommonCallbackData, ConversationMode
from samanthas_telegram_bot.conversation.auxil.helpers import (
    make_buttons_yes_no,
    make_dict_for_message_to_ask_age_student,
    make_dict_for_message_with_inline_keyboard,
)
from samanthas_telegram_bot.data_structures.constants import Locale
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import Role


class MessageSender:
    """A helper class that sends replies to user by executing
    `update.effective_chat.send_message()`.

    Methods in this class are called several times in the bot's code and/or are complex.

    All methods in this class are **static methods**. This is a class is just a namespace
    and a way to be stylistically consistent with other helper classes.
    """

    @staticmethod
    async def ask_age_student(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
        """Asks student about their age group."""
        await update.effective_message.reply_text(
            **make_dict_for_message_to_ask_age_student(context)
        )

    @classmethod
    async def ask_age_teacher(cls, update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
        """Asks teacher if they are 18+."""
        await cls.ask_yes_no(update, context, question_phrase_internal_id="ask_if_18")

    @staticmethod
    async def ask_phone_number(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
        """Sends a message to ask for phone number."""
        locale: Locale = context.user_data.locale

        reply_markup = ReplyKeyboardMarkup(
            [
                [
                    KeyboardButton(
                        text=context.bot_data.phrases["share_phone"][locale],
                        request_contact=True,
                    )
                ]
            ],
            one_time_keyboard=True,
        )

        await update.effective_chat.send_message(
            context.bot_data.phrases["ask_phone"][locale],
            disable_web_page_preview=True,  # the message contains link to site with country codes
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
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

        if (
            data.role == Role.TEACHER
            and context.chat_data.mode == ConversationMode.REGISTRATION_MAIN_FLOW
        ):
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
                    ]  # each button in its own row
                    for option in (CommonCallbackData.YES, CommonCallbackData.NO)
                ]
            ),
        )

    @classmethod
    async def ask_student_with_high_level_if_wants_speaking_club(
        cls, update: Update, context: CUSTOM_CONTEXT_TYPES
    ) -> None:
        """Asks student whose level of English is too high if they want to join Speaking Club."""
        await cls.ask_yes_no(
            update, context, question_phrase_internal_id="student_level_too_high_ask"
        )

    @staticmethod
    async def ask_yes_no(
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        question_phrase_internal_id: str,
        parse_mode: ParseMode | None = None,
    ) -> None:
        """Asks "yes" or "no" (localized)."""
        await update.message.reply_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases[question_phrase_internal_id][
                    context.user_data.locale
                ],
                buttons=make_buttons_yes_no(context),
                buttons_per_row=2,
                parse_mode=parse_mode,
            )
        )

    @staticmethod
    def _prepare_message_for_review(update: Update, context: CUSTOM_CONTEXT_TYPES) -> str:
        """Prepares text message with user info for review, depending on role and other factors."""
        data = context.user_data
        locale: Locale = data.locale
        phrases = context.bot_data.phrases

        message = (
            f"{phrases['ask_review'][locale]}\n\n"
            f"{phrases['review_first_name'][locale]}: {data.first_name}\n"
            f"{phrases['review_last_name'][locale]}: {data.last_name}\n"
            f"{phrases['review_email'][locale]}: {data.email}\n"
        )

        if data.role == Role.STUDENT:
            message += (
                f"{phrases['review_student_age_group'][locale]}: "
                f"{data.student_age_from}-{data.student_age_to}\n"
            )
        # TODO add students' age ranges for teacher? This will require changes to UserData

        if data.tg_username:
            message += f"{phrases['review_username'][locale]} (@{data.tg_username})\n"
        if data.phone_number:
            message += f"{phrases['review_phone_number'][locale]}: {data.phone_number}\n"

        offset_hour = data.utc_offset_hour
        offset_minute = str(data.utc_offset_minute).zfill(2)  # to produce "00" from 0

        if data.utc_offset_hour > 0:
            message += f"{phrases['review_timezone'][locale]}: UTC+{offset_hour}"
        elif data.utc_offset_hour < 0:
            message += f"{phrases['review_timezone'][locale]}: UTC{offset_hour}"
        else:
            message += f"\n{phrases['review_timezone'][locale]}: UTC"

        utc_time = datetime.datetime.now(tz=datetime.timezone.utc)
        now_with_offset = utc_time + datetime.timedelta(
            hours=data.utc_offset_hour, minutes=data.utc_offset_minute
        )
        message += (
            f" ({phrases['current_time'][locale]} " f"{now_with_offset.strftime('%H:%M')})\n"
        )

        message += f"\n{phrases['review_availability'][locale]}:\n"

        slot_ids = sorted(data.day_and_time_slot_ids)
        # creating a dictionary matching days to lists of slots, so that slots can be shown to
        # user grouped by a day of the week
        slot_id_for_day_index: dict[int, list[int]] = defaultdict(list)

        for slot_id in slot_ids:
            slot_id_for_day_index[
                context.bot_data.day_and_time_slot_for_slot_id[slot_id].day_of_week_index
            ].append(slot_id)

        for day_index in slot_id_for_day_index:
            message += f"{phrases['ask_slots_' + str(day_index)][locale]}: "

            for slot_id in slot_id_for_day_index[day_index]:
                slot = context.bot_data.day_and_time_slot_for_slot_id[slot_id]

                # User must see their slots in their chosen timezone.
                # % 24 is needed to avoid showing 22:00-25:00 to the user
                message += (
                    f" {(slot.from_utc_hour + offset_hour) % 24}:{offset_minute}-"
                    f"{(slot.to_utc_hour + offset_hour) % 24}:{offset_minute};"
                )
            else:  # remove last semicolon, end day with line break
                message = message[:-1] + "\n"
        message += "\n"

        # Because of complex logic around English, we will not offer the student to review their
        # language/level for now.  This option will be reserved for teachers.
        if data.role == Role.TEACHER:
            message += f"{phrases['review_languages_levels'][locale]}:\n"
            for language in data.levels_for_teaching_language:
                message += f"{phrases[language][locale]}: "
                message += ", ".join(sorted(data.levels_for_teaching_language[language])) + "\n"
            message += "\n"

        message += f"{phrases['review_communication_language'][locale]}: "
        message += (
            phrases[f"class_communication_language_option_{data.communication_language_in_class}"][
                locale
            ]
            + "\n"
        )

        return message
