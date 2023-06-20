import asyncio
import logging
import typing

import phonenumbers
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonCommands,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import ConversationHandler

from samanthas_telegram_bot.api_queries.api_client import ApiClient
from samanthas_telegram_bot.api_queries.auxil.enums import LoggingLevel
from samanthas_telegram_bot.api_queries.smalltalk import get_smalltalk_result
from samanthas_telegram_bot.auxil.log_and_notify import log_and_notify
from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.conversation.auxil.enums import CommonCallbackData, ConversationMode
from samanthas_telegram_bot.conversation.auxil.enums import ConversationStateCommon as CommonState
from samanthas_telegram_bot.conversation.auxil.enums import (
    ConversationStateStudent as StudentState,
)
from samanthas_telegram_bot.conversation.auxil.enums import (
    ConversationStateTeacher as TeacherState,
)
from samanthas_telegram_bot.conversation.auxil.message_sender import MessageSender
from samanthas_telegram_bot.conversation.auxil.shortcuts import answer_callback_query_and_get_data
from samanthas_telegram_bot.data_structures.constants import EMAIL_PATTERN, LOCALES, Locale
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import Role

logger = logging.getLogger(__name__)


async def start(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Starts the conversation and asks the user about the interface language.

    The interface language may not match the interface language of the phone, so better to ask.
    """

    context.user_data.clear_student_data()
    context.user_data.chat_id = update.effective_chat.id
    logger.info(f"Chat ID: {context.user_data.chat_id}")

    context.chat_data.mode = ConversationMode.NORMAL

    await update.effective_chat.set_menu_button(MenuButtonCommands())

    # Set the iterable attributes to empty lists/sets to avoid TypeError/KeyError later on.
    # Methods handling these iterables can be called from different callbacks, so better to set
    # them here, in one place.
    context.user_data.day_and_time_slot_ids = []
    context.user_data.language_and_level_ids = []
    context.user_data.levels_for_teaching_language = {}
    context.user_data.non_teaching_help_types = []
    context.user_data.teacher_student_age_range_ids = []

    # We will be storing the selected options in boolean flags of TeacherPeerHelp(),
    # but in order to remove selected options from InlineKeyboard, I have to store exact
    # callback_data somewhere.
    context.chat_data.peer_help_callback_data = set()

    # set day of week to Monday to start asking about slots for each day
    context.chat_data.day_index = 0

    greeting = "🚧 ТЕСТОВИЙ РЕЖИМ \| TEST MODE 🚧\n\n"  # noqa # TODO remove going to production
    greeting += "👋 "
    for locale in LOCALES:
        greeting += (
            rf"{context.bot_data.phrases['hello'][locale]} {update.message.from_user.first_name}\!"
            f" {context.bot_data.phrases['choose_language_of_conversation'][locale]}\n\n"
        )

    await update.message.reply_text(
        greeting,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(text="українською", callback_data="ua")],
                [InlineKeyboardButton(text="in English", callback_data="en")],
                [InlineKeyboardButton(text="по-русски", callback_data="ru")],
            ]
        ),
        disable_web_page_preview=True,
    )

    return CommonState.IS_REGISTERED


async def store_locale_ask_if_already_registered(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores the interface language and asks the user if they are already registered."""

    query, context.user_data.locale = await answer_callback_query_and_get_data(update)

    await CQReplySender.ask_yes_no(
        context,
        query,
        question_phrase_internal_id="ask_already_with_us",
    )

    return CommonState.CHECK_CHAT_ID_ASK_TIMEZONE


async def redirect_to_coordinator_if_registered_check_chat_id_ask_timezone(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Checks user's answer if they are registered, checks chat ID, asks timezone.

    If user is already registered (as per their answer), redirects to coordinator.
    Otherwise, checks if Telegram chat ID is already present in the back end.
    If it is, asks the user if they still want to proceed with registration.

    If the user said they were not registered and chat ID was not found,
    asks timezone.
    """
    # TODO ask role right here
    query, data = await answer_callback_query_and_get_data(update)

    if data == CommonCallbackData.YES:
        await query.edit_message_text(
            context.bot_data.phrases["reply_go_to_other_chat"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return ConversationHandler.END

    if await ApiClient.chat_id_is_registered(chat_id=update.effective_chat.id):
        await CQReplySender.ask_yes_no(
            context, query, question_phrase_internal_id="reply_chat_id_found"
        )
        return CommonState.CHECK_IF_WANTS_TO_REGISTER_ANOTHER_PERSON_ASK_TIMEZONE

    await CQReplySender.ask_timezone(context, query)
    return CommonState.ASK_FIRST_NAME


async def say_bye_if_does_not_want_to_register_another_or_ask_timezone(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If user does not want to register another person, says bye. Otherwise, asks timezone."""

    query, data = await answer_callback_query_and_get_data(update)

    if data == CommonCallbackData.NO:
        await query.edit_message_text(
            context.bot_data.phrases["bye_wait_for_message_from_bot"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return ConversationHandler.END

    await CQReplySender.ask_timezone(context, query)
    return CommonState.ASK_FIRST_NAME


async def store_timezone_ask_first_name(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores UTC offset, asks first name."""
    query, data = await answer_callback_query_and_get_data(update)

    context.user_data.utc_offset_hour, context.user_data.utc_offset_minute = (
        int(item) for item in data.split(":")
    )

    if context.chat_data.mode == ConversationMode.REVIEW:
        await MessageSender.ask_review(update, context)
        return CommonState.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    await query.edit_message_text(
        context.bot_data.phrases["ask_first_name"][context.user_data.locale],
        reply_markup=InlineKeyboardMarkup([]),
    )
    return CommonState.ASK_LAST_NAME


async def store_first_name_ask_last_name(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the first name and asks the last name."""

    # It is better for less ambiguity to ask first name and last name in separate questions

    # It is impossible to send an empty message, but if for some reason user edits their previous
    # message, an update will be issued, but .message attribute will be none.
    # This will trigger an exception, although the bot won't stop working.  Still we don't want it.
    # So in this case just wait for user to type in the actual new message by returning him to the
    # same state again.
    # This "if" can't be easily factored out because the state returned is different in every
    # callback.
    # TODO an enhancement could be to store the information from the edited message
    if update.message is None:
        return CommonState.ASK_LAST_NAME

    context.user_data.first_name = update.message.text

    if context.chat_data.mode == ConversationMode.REVIEW:
        await update.message.delete()
        await MessageSender.ask_review(update, context)
        return CommonState.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    await update.message.reply_text(
        context.bot_data.phrases["ask_last_name"][context.user_data.locale]
    )
    return CommonState.ASK_SOURCE


async def store_last_name_ask_source(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the last name and asks the user how they found out about Samantha's Group."""

    if update.message is None:
        return CommonState.ASK_SOURCE

    context.user_data.last_name = update.message.text

    if context.chat_data.mode == ConversationMode.REVIEW:
        await update.message.delete()
        await MessageSender.ask_review(update, context)
        return CommonState.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    await update.effective_chat.send_message(
        context.bot_data.phrases["ask_source"][context.user_data.locale]
    )
    return CommonState.CHECK_USERNAME


async def store_source_check_username(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the source of knowledge about SSG, checks Telegram nickname or asks for
    phone number.
    """

    if update.message is None:
        return CommonState.CHECK_USERNAME

    context.user_data.source = update.message.text

    if update.effective_user.username:
        await MessageSender.ask_store_username(update, context)

    return CommonState.ASK_PHONE_NUMBER


async def store_username_if_available_ask_phone_or_email(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If user's username was empty, or they chose to provide a phone number, ask for it.

    If the user provides their username, ask their email (skip asking for phone number).
    """

    username = update.effective_user.username

    query, data = await answer_callback_query_and_get_data(update)

    if data == "store_username_yes" and username:
        context.user_data.phone_number = None  # in case it was entered at previous run of the bot
        context.user_data.tg_username = username
        logger.info(
            f"Chat {update.effective_chat.id}. Username {username} will be stored in the database."
        )
        await query.edit_message_text(
            context.bot_data.phrases["ask_email"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return CommonState.ASK_ROLE

    context.user_data.tg_username = None
    await query.delete_message()

    await MessageSender.ask_phone_number(update, context)
    return CommonState.ASK_EMAIL


async def store_phone_ask_email(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the phone number and asks for email."""

    if update.message is None:
        return CommonState.ASK_EMAIL

    locale: Locale = context.user_data.locale

    # 1. Read phone number
    phone_number_to_parse = (
        update.message.contact.phone_number if update.message.contact else update.message.text
    )
    # Hyphens, spaces, parentheses are OK for `phonenumbers`, but some devices leave out the "+"
    # even when sharing the contact
    if not (phone_number_to_parse.startswith("00") or phone_number_to_parse.startswith("+")):
        phone_number_to_parse = f"+{phone_number_to_parse}"

    # 2. Parse phone number
    try:
        # Specifying a European region (Ireland in this case) will allow for both
        # "+<country_code><number>" and "00<country_code><number>" to be parsed correctly.
        # Any European region would work (GB, DE, etc.).  Ireland is used for sentimental reasons.
        parsed_phone_number = phonenumbers.parse(number=phone_number_to_parse, region="IE")
    except phonenumbers.phonenumberutil.NumberParseException:
        logger.info(
            f"Chat {update.effective_chat.id}. "
            f"Could not parse phone number {phone_number_to_parse}"
        )
        parsed_phone_number = None

    # 3. Check validity and return user to same state if phone number not valid
    if parsed_phone_number and phonenumbers.is_valid_number(parsed_phone_number):
        context.user_data.phone_number = phonenumbers.format_number(
            parsed_phone_number, phonenumbers.PhoneNumberFormat.E164
        )
    else:
        logger.info(
            f"Chat {update.effective_chat.id}. Invalid phone number {parsed_phone_number} "
            f"(parsed from {phone_number_to_parse})"
        )
        await update.message.reply_text(
            f"{phone_number_to_parse} {context.bot_data.phrases['invalid_phone_number'][locale]}",
        )
        return CommonState.ASK_EMAIL

    if context.chat_data.mode == ConversationMode.REVIEW:
        await update.message.delete()
        await MessageSender.ask_review(update, context)
        return CommonState.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    await update.message.reply_text(context.bot_data.phrases["ask_email"][locale])
    logger.info(f"Chat {update.effective_chat.id}. Phone: {context.user_data.phone_number}")
    return CommonState.ASK_ROLE


async def store_email_check_existence_ask_role(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores the email, checks existence and asks whether user wants to be student or teacher.

    Stores the email. If the user with these contact details exists, redirects to goodbye.
    Otherwise, asks whether the user wants to be a student or a teacher.
    """

    if update.message is None:
        return CommonState.ASK_ROLE

    locale: Locale = context.user_data.locale

    email = update.message.text.strip()
    if not EMAIL_PATTERN.match(email):
        await update.message.reply_text(context.bot_data.phrases["invalid_email"][locale])
        return CommonState.ASK_ROLE

    context.user_data.email = email

    # terminate conversation if the person with these personal data already exists
    if await ApiClient.person_with_first_name_last_name_email_exists_in_database(
        first_name=context.user_data.first_name,
        last_name=context.user_data.last_name,
        email=context.user_data.email,
    ):
        await update.message.reply_text(context.bot_data.phrases["user_already_exists"][locale])
        return ConversationHandler.END

    if context.chat_data.mode == ConversationMode.REVIEW:
        await update.message.delete()
        await MessageSender.ask_review(update, context)
        return CommonState.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    await update.message.reply_text(
        context.bot_data.phrases["ask_role"][locale],
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=context.bot_data.phrases[f"option_{role}"][locale],
                        callback_data=role,
                    )
                    for role in (Role.STUDENT, Role.TEACHER)
                ],
            ]
        ),
    )
    return CommonState.ASK_AGE


async def store_role_ask_age(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the role and asks the user what their age is (the question depends on role)."""

    query, context.user_data.role = await answer_callback_query_and_get_data(update)

    match context.user_data.role:
        case Role.STUDENT:
            await CQReplySender.ask_student_age(context, query)
            return StudentState.TIME_SLOTS_START
        case Role.TEACHER:
            await CQReplySender.ask_yes_no(
                context,
                query,
                question_phrase_internal_id="ask_if_18",
            )
            return TeacherState.TIME_SLOTS_START_OR_ASK_YOUNG_TEACHER_ABOUT_SPEAKING_CLUB
        case _:
            raise NotImplementedError(f"{context.user_data.role=} not supported")


async def store_one_time_slot_ask_another(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores one time slot and offers to choose another."""
    query, data = await answer_callback_query_and_get_data(update)
    context.user_data.day_and_time_slot_ids.append(int(data))

    await CQReplySender.ask_time_slot(context, query)
    return CommonState.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE


async def store_last_time_slot_ask_slots_for_next_day_or_teaching_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores last time slot, asks teaching language."""
    # not using shortcut here because the query may need to be answered with an alert
    query = update.callback_query

    chat_data = context.chat_data
    user_data = context.user_data

    # If we haven't yet reached Sunday, move on to next day and ask slots for it
    if chat_data.day_index < 6:
        chat_data.day_index += 1
        await query.answer()
        await CQReplySender.ask_time_slot(context, query)
        return CommonState.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE

    # We have reached Sunday
    slots_for_logging = (
        context.bot_data.day_and_time_slot_for_slot_id[slot_id]
        for slot_id in sorted(user_data.day_and_time_slot_ids)
    )
    logger.info(
        f"Chat {update.effective_chat.id}. "
        f"Slots: {', '.join(str(slot) for slot in slots_for_logging)}",
    )

    # reset day of week to Monday for possible review or re-run
    chat_data.day_index = 0

    if not any(user_data.day_and_time_slot_ids):
        await query.answer(
            context.bot_data.phrases["no_slots_selected"][user_data.locale],
            show_alert=True,
        )
        logger.info(f"Chat {update.effective_chat.id}. User has selected no slots at all")
        await CQReplySender.ask_time_slot(context, query)
        return CommonState.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE

    if chat_data.mode == ConversationMode.REVIEW:
        await query.answer()
        await MessageSender.ask_review(update, context)
        return CommonState.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    # If we've reached this part of function, it means that we have reached Sunday,
    # user has selected some slots, and we're not in review mode.
    # Time to ask about teaching language.

    await query.answer()
    await CQReplySender.ask_teaching_languages(context, query, show_done_button=False)

    # This is the bifurcation point in the conversation: next state depends on role.
    if user_data.role == Role.TEACHER:
        return TeacherState.ASK_LEVEL_OR_ANOTHER_LANGUAGE_OR_COMMUNICATION_LANGUAGE
    elif user_data.role == Role.STUDENT:
        return StudentState.ASK_LEVEL_OR_COMMUNICATION_LANGUAGE_OR_START_TEST
    else:
        raise NotImplementedError(
            f"Move from time slots to next state not supported for {user_data.role=}"
        )


# ==== END-OF-CONVERSATION CALLBACKS BEGIN ====


async def ask_final_comment(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Asks final comment."""
    query, _ = await answer_callback_query_and_get_data(update)

    # We don't call edit_message_text(): let user info remain in the chat for user to see,
    # but remove the buttons.
    await query.edit_message_reply_markup(InlineKeyboardMarkup([]))
    await update.effective_chat.send_message(
        context.bot_data.phrases["ask_final_comment"][context.user_data.locale],
        reply_markup=InlineKeyboardMarkup([]),
    )
    return CommonState.BYE


async def show_review_menu(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Shows review menu to the user."""
    query, _ = await answer_callback_query_and_get_data(update)

    # Switch into review mode to let other callbacks know that they should return user
    # back to the review callback instead of moving him normally along the conversation line
    context.chat_data.mode = ConversationMode.REVIEW
    await CQReplySender.ask_review_category(context, query)
    return CommonState.REVIEW_REQUESTED_ITEM


async def store_additional_help_comment_ask_final_comment(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """For young teachers: stores comment on additional help, asks for final comment."""
    if update.message is None:
        return CommonState.ASK_FINAL_COMMENT
    locale: Locale = context.user_data.locale

    context.user_data.teacher_additional_skills_comment = update.message.text

    # We want to give the young teacher the opportunity to double-check their email
    # without starting a full-fledged review
    await update.message.reply_text(
        f"{context.bot_data.phrases['young_teacher_we_will_email_you'][locale]} "
        f"{context.user_data.email}\n\n"
        f"{context.bot_data.phrases['ask_final_comment'][locale]}"
    )
    return CommonState.BYE


async def store_comment_end_conversation(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores comment and ends the conversation.

    For a would-be teacher that is under 18, stores their comment about potential useful skills.
    For others, stores the general comment. Ends the conversation."""
    user_data = context.user_data
    locale: Locale = user_data.locale

    user_data.comment = update.message.text

    await update.effective_chat.send_message(context.bot_data.phrases["processing_wait"][locale])

    # number of groups is None for young teachers and 0 for adults that only want speaking club
    if user_data.role == Role.TEACHER and not user_data.teacher_number_of_groups:
        phrase_id = "bye_wait_for_message_from_coordinator"
    elif user_data.role == Role.STUDENT and user_data.student_needs_oral_interview is True:
        phrase_id = "bye_go_to_chat_with_coordinator"
    else:
        phrase_id = "bye_wait_for_message_from_bot"

    if user_data.role == Role.STUDENT:
        if user_data.student_needs_oral_interview:
            await _set_student_language_and_level_for_english_starters(update, context)
        elif user_data.student_agreed_to_smalltalk:
            await _process_student_language_and_level_from_smalltalk(update, context)
        result = await ApiClient.create_student(update, context)
    elif user_data.role == Role.TEACHER:
        if user_data.teacher_is_under_18:
            result = await ApiClient.create_teacher_under_18(update, context)
        else:
            result = await ApiClient.create_teacher(update, context)
    else:
        result = False

    if result is True:
        await update.effective_chat.send_message(context.bot_data.phrases[phrase_id][locale])
    else:
        await log_and_notify(
            bot=context.bot,
            logger=logger,
            text=f"Cannot send to backend: {user_data=}",
            level=LoggingLevel.CRITICAL,
        )

    return ConversationHandler.END


async def cancel(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Cancels and ends the conversation."""

    logger.info(f"Chat {update.effective_chat.id}. User canceled the conversation.")

    # the /cancel command could come even before the user chooses the locale
    if context.user_data.locale:
        locale: Locale = context.user_data.locale
    else:
        locale = typing.cast(Locale, update.effective_user.language_code)

    await update.message.reply_text(
        context.bot_data.phrases["bye_cancel"][locale], reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def send_help(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
    """Displays help message."""

    await update.message.reply_text(
        "Enter /start to start the conversation!", reply_markup=ReplyKeyboardRemove()
    )


async def _process_student_language_and_level_from_smalltalk(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> None:
    """Performs operations that are necessary to determine student's level of English.

    For all other languages, the logic is simple because there are no assessments.
    Language level is stored right after user chooses it during the conversation.
    """
    user_data = context.user_data
    user_data.student_smalltalk_result = await get_smalltalk_result(update, context)

    if user_data.student_smalltalk_result and user_data.student_smalltalk_result.level:
        level = user_data.student_smalltalk_result.level
        logger.info(f"Chat {update.effective_chat.id}. Setting {level=} based on SmallTalk test.")
    else:
        level = user_data.student_assessment_resulting_level
        logger.info(
            f"Chat {update.effective_chat.id}. No SmallTalk result loaded or level "
            f"is None. Using {level=} from written assessment."
        )

    user_data.language_and_level_ids = [
        context.bot_data.language_and_level_id_for_language_id_and_level[("en", level)]
    ]


async def _set_student_language_and_level_for_english_starters(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> None:
    user_data = context.user_data
    if user_data.student_needs_oral_interview:
        user_data.language_and_level_ids = [
            context.bot_data.language_and_level_id_for_language_id_and_level[("en", "A0")]
        ]
        logger.info(
            f"Chat {update.effective_chat.id}. "
            f"Setting level formally to A0 ({user_data.language_and_level_ids}) "
            f"because user needs oral interview in English"
        )
        user_data.comment = f"{user_data.comment}\n- NEEDS ORAL INTERVIEW!"


async def message_fallback(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
    await update.message.delete()
    locale = context.user_data.locale
    if locale is None:
        locale = "ua"
    message = await update.effective_chat.send_message(
        context.bot_data.phrases["message_fallback"][locale]
    )
    await asyncio.sleep(5)
    await message.delete()
