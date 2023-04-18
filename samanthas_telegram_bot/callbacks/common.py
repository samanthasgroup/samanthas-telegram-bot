import logging
import re
from collections import defaultdict

import phonenumbers
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonCommands,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ConversationHandler

from samanthas_telegram_bot.api_queries import (
    chat_id_is_registered,
    get_age_ranges,
    person_with_first_name_last_name_email_exists_in_database,
)
from samanthas_telegram_bot.assessment import prepare_assessment
from samanthas_telegram_bot.callbacks.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.callbacks.auxil.message_sender import MessageSender
from samanthas_telegram_bot.callbacks.auxil.utils import answer_callback_query_and_get_data
from samanthas_telegram_bot.constants import (
    DAY_OF_WEEK_FOR_INDEX,
    EMAIL_PATTERN,
    LOCALES,
    NON_TEACHING_HELP_TYPES,
    PHRASES,
    CallbackData,
    ChatMode,
    Role,
    State,
    UserDataReviewCategory,
)
from samanthas_telegram_bot.custom_context_types import CUSTOM_CONTEXT_TYPES

logger = logging.getLogger(__name__)


async def start(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Starts the conversation and asks the user about the interface language.

    The interface language may not match the interface language of the phone, so better to ask.
    """

    # TODO if user clears the history after starting, they won't be able to start until they cancel
    logger.info(f"Chat ID: {update.effective_chat.id}")

    context.chat_data["age_ranges"] = await get_age_ranges(logger=logger)
    context.chat_data["mode"] = ChatMode.NORMAL

    await update.effective_chat.set_menu_button(MenuButtonCommands())

    # Set the iterable attributes to empty lists/sets to avoid TypeError/KeyError later on.
    # Methods handling these iterables can be called from different callbacks, so better to set
    # them here, in one place.
    context.user_data.non_teaching_help_types = []
    context.user_data.teacher_age_groups_of_students = []

    # TODO maybe remove this altogether and produce a list like with non-teaching help
    # We will be storing the selected options in boolean flags of TeacherPeerHelp(),
    # but in order to remove selected options from InlineKeyboard, I have to store exact
    # callback_data somewhere.
    context.chat_data["peer_help_callback_data"] = set()

    greeting = "👋 "
    for locale in LOCALES:
        greeting += (
            f"{PHRASES['hello'][locale]} {update.message.from_user.first_name}! "
            f"{PHRASES['choose_language_of_conversation'][locale]}\n\n"
        )

    await update.message.reply_text(
        greeting,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="українською",
                        callback_data="ua",
                    ),
                    InlineKeyboardButton(
                        text="in English",
                        callback_data="en",
                    ),
                    InlineKeyboardButton(
                        text="по-русски",
                        callback_data="ru",
                    ),
                ],
            ]
        ),
    )

    return State.IS_REGISTERED


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

    return State.CHECK_CHAT_ID_ASK_FIRST_NAME


async def redirect_to_coordinator_if_registered_check_chat_id_ask_first_name(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Checks user's answer if they are registered, checks chat ID, asks for first name.

    If user is already registered (as per their answer), redirects to coordinator.
    Otherwise, checks if Telegram chat ID is already present in the back end.
    If it is, asks the user if they still want to proceed with registration.

    If the user said they were not registered and chat ID was not found,
    asks for first name.
    """

    query, data = await answer_callback_query_and_get_data(update)

    if data == CallbackData.YES:
        await query.edit_message_text(
            PHRASES["reply_go_to_other_chat"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return ConversationHandler.END

    if await chat_id_is_registered(chat_id=update.effective_chat.id, logger=logger):
        await CQReplySender.ask_yes_no(
            context, query, question_phrase_internal_id="reply_chat_id_found"
        )
        return State.CHECK_IF_WANTS_TO_REGISTER_ANOTHER_PERSON_ASK_FIRST_NAME

    await query.edit_message_text(
        PHRASES["ask_first_name"][context.user_data.locale],
        reply_markup=InlineKeyboardMarkup([]),
    )
    return State.ASK_LAST_NAME


async def say_bye_if_does_not_want_to_register_another_or_ask_first_name(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If user does not want to register another person, says bye. Otherwise, asks first name."""

    query, data = await answer_callback_query_and_get_data(update)

    if data == CallbackData.NO:
        await query.edit_message_text(
            PHRASES["bye_wait_for_message_from_bot"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return ConversationHandler.END

    await query.edit_message_text(
        PHRASES["ask_first_name"][context.user_data.locale],
        reply_markup=InlineKeyboardMarkup([]),
    )
    return State.ASK_LAST_NAME


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
        return State.ASK_LAST_NAME

    context.user_data.first_name = update.message.text

    if context.chat_data["mode"] == ChatMode.REVIEW:
        await update.message.delete()
        await MessageSender.ask_review(update, context)
        return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    await update.message.reply_text(PHRASES["ask_last_name"][context.user_data.locale])
    return State.ASK_SOURCE


async def store_last_name_ask_source(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the last name and asks the user how they found out about Samantha's Group."""

    if update.message is None:
        return State.ASK_SOURCE

    context.user_data.last_name = update.message.text

    if context.chat_data["mode"] == ChatMode.REVIEW:
        await update.message.delete()
        await MessageSender.ask_review(update, context)
        return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    await update.effective_chat.send_message(PHRASES["ask_source"][context.user_data.locale])
    return State.CHECK_USERNAME


async def store_source_check_username(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the source of knowledge about SSG, checks Telegram nickname or asks for
    phone number.
    """

    if update.message is None:
        return State.CHECK_USERNAME

    context.user_data.source = update.message.text

    if update.effective_user.username:
        await MessageSender.ask_store_username(update, context)

    return State.ASK_PHONE_NUMBER


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
        logger.info(f"Username: {username}. Will be stored in the database.")
        await query.edit_message_text(
            PHRASES["ask_email"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return State.ASK_ROLE

    context.user_data.tg_username = None
    await query.delete_message()

    await MessageSender.ask_phone_number(update, context)
    return State.ASK_EMAIL


async def store_phone_ask_email(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the phone number and asks for email."""

    if update.message is None:
        return State.ASK_EMAIL

    # 1. Read phone number
    # (hyphens, spaces, parentheses are no problem for `phonenumbers`, so no pre-processing needed)
    phone_number_to_parse = (
        update.message.contact.phone_number if update.message.contact else update.message.text
    )

    # 2. Parse phone number
    try:
        # Specifying a European region (Ireland in this case) will allow for both
        # "+<country_code><number>" and "00<country_code><number>" to be parsed correctly.
        # Any European region would work (GB, DE, etc.).  Ireland is used for sentimental reasons.
        parsed_phone_number = phonenumbers.parse(number=phone_number_to_parse, region="IE")
    except phonenumbers.phonenumberutil.NumberParseException:
        logger.info(f"Could not parse phone number {phone_number_to_parse}")
        parsed_phone_number = None

    # 3. Check validity and return user to same state if phone number not valid
    if parsed_phone_number and phonenumbers.is_valid_number(parsed_phone_number):
        context.user_data.phone_number = phonenumbers.format_number(
            parsed_phone_number, phonenumbers.PhoneNumberFormat.E164
        )
    else:
        await update.message.reply_text(
            PHRASES["invalid_phone_number"][context.user_data.locale],
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.ASK_EMAIL

    if context.chat_data["mode"] == ChatMode.REVIEW:
        await update.message.delete()
        await MessageSender.ask_review(update, context)
        return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    await update.message.reply_text(
        PHRASES["ask_email"][context.user_data.locale],
        reply_markup=ReplyKeyboardRemove(),
    )
    logger.info(f"Phone: {context.user_data.phone_number}")
    return State.ASK_ROLE


async def store_email_check_existence_ask_role(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores the email, checks existence and asks whether user wants to be student or teacher.

    Stores the email. If the user with these contact details exists, redirects to goodbye.
    Otherwise, asks whether the user wants to be a student or a teacher.
    """

    if update.message is None:
        return State.ASK_ROLE

    locale = context.user_data.locale

    email = update.message.text.strip()
    if not EMAIL_PATTERN.match(email):
        await update.message.reply_text(
            PHRASES["invalid_email"][locale],
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.ASK_ROLE

    context.user_data.email = email

    # terminate conversation if the person with these personal data already exists
    if await person_with_first_name_last_name_email_exists_in_database(
        first_name=context.user_data.first_name,
        last_name=context.user_data.last_name,
        email=context.user_data.email,
        logger=logger,
    ):
        await update.message.reply_text(PHRASES["user_already_exists"][locale])
        return ConversationHandler.END

    if context.chat_data["mode"] == ChatMode.REVIEW:
        await update.message.delete()
        await MessageSender.ask_review(update, context)
        return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    await update.message.reply_text(
        PHRASES["ask_role"][locale],
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=PHRASES[f"option_{role}"][locale],
                        callback_data=role,
                    )
                    for role in (Role.STUDENT, Role.TEACHER)
                ],
            ]
        ),
    )
    return State.ASK_AGE


async def store_role_ask_age(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the role and asks the user what their age is (the question depends on role)."""

    query, context.user_data.role = await answer_callback_query_and_get_data(update)

    if context.user_data.role == Role.TEACHER:
        await CQReplySender.ask_yes_no(
            context,
            query,
            question_phrase_internal_id="ask_if_18",
        )
    else:
        await CQReplySender.ask_student_age(context, query)

    return State.ASK_TIMEZONE


async def store_age_ask_timezone(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores age group for student, asks timezone. Action for teacher depends on their age.

    If user is a teacher under 18, informs that teachers under 18 are not allowed and asks
    whether they are at least 16, in which case they can host speaking clubs.
    """

    query, data = await answer_callback_query_and_get_data(update)

    if context.user_data.role == Role.TEACHER:
        if data == CallbackData.YES:  # yes, the teacher is 18 or older
            context.user_data.teacher_is_under_18 = False
        else:
            context.user_data.teacher_is_under_18 = True
            await CQReplySender.ask_teacher_is_over_16_and_ready_to_host_speaking_clubs(
                context, query
            )
            return State.ASK_YOUNG_TEACHER_ADDITIONAL_HELP

    if context.user_data.role == Role.STUDENT:
        context.user_data.student_age_from, context.user_data.student_age_to = (
            int(item) for item in data.split("-")
        )
        logger.info(
            f"Age group: {context.user_data.student_age_from}-{context.user_data.student_age_to}"
        )

    if context.chat_data["mode"] == ChatMode.REVIEW:
        await query.delete_message()
        await MessageSender.ask_review(update, context)
        return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    await CQReplySender.ask_timezone(context, query)
    return State.TIME_SLOTS_START


async def store_timezone_ask_slots_for_one_day_or_teaching_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If this function is called for the first time in a conversation, **stores the timezone**
    and gives time slots for Monday.

    If this function is called after choosing time slots for a day, asks for time slots for the
    next day.

    If this is the last day, makes asks for the first language to learn/teach.
    """

    query = update.callback_query

    if re.match(r"^[+-]?\d{1,2}$", query.data):  # this is a UTC offset
        await query.answer()
        context.user_data.utc_offset = int(query.data)

        if context.chat_data["mode"] == ChatMode.REVIEW:
            await query.delete_message()
            await MessageSender.ask_review(update, context)
            return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

        context.user_data.time_slots_for_day = defaultdict(list)

        # set day of week to Monday to start asking about slots for each day
        context.chat_data["day_idx"] = 0

    elif query.data == CallbackData.NEXT:  # user pressed "next" button after choosing slots
        if context.chat_data["day_idx"] == 6:  # we have reached Sunday
            logger.info(context.user_data.time_slots_for_day)

            if not any(context.user_data.time_slots_for_day.values()):
                await query.answer(
                    PHRASES["no_slots_selected"][context.user_data.locale], show_alert=True
                )
                logger.info("User has selected no slots at all")
                context.chat_data["day_idx"] = 0
                await CQReplySender.ask_time_slot(context, query)
                return State.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE

            await query.answer()

            if context.chat_data["mode"] == ChatMode.REVIEW:
                await query.delete_message()
                await MessageSender.ask_review(update, context)
                return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

            context.user_data.levels_for_teaching_language = {}
            # if the dictionary is empty, it means that no language was chosen yet.
            # In this case no "done" button must be shown.
            show_done_button = True if context.user_data.levels_for_teaching_language else False
            await CQReplySender.ask_teaching_languages(
                context, query, show_done_button=show_done_button
            )
            return State.ASK_LEVEL_OR_ANOTHER_TEACHING_LANGUAGE_OR_COMMUNICATION_LANGUAGE
        context.chat_data["day_idx"] += 1

    await query.answer()
    await CQReplySender.ask_time_slot(context, query)

    return State.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE


async def store_one_time_slot_ask_another(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores one time slot and offers to choose another."""
    query, data = await answer_callback_query_and_get_data(update)

    day = DAY_OF_WEEK_FOR_INDEX[context.chat_data["day_idx"]]
    context.user_data.time_slots_for_day[day].append(data)

    await CQReplySender.ask_time_slot(context, query)

    return State.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE


async def store_teaching_language_ask_another_or_level_or_communication_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores teaching language. Next actions depend on role and other factors.

    Stores teaching language.

    If the user is a student and selected English, asks for the ability to read in English
    instead of asking for level.

    If the user is a teacher or a student that wants to learn a language other than English,
    asks for level.

    If the user is a teacher and is done choosing levels, offers to choose another language.

    If the user is a teacher and has finished choosing languages, asks about language of
    communication in class.
    """

    query, data = await answer_callback_query_and_get_data(update)

    # Students can only choose one language, so callback_data == "done" is only possible
    # for a teacher, but we'll keep it explicit here
    if data == CallbackData.DONE and context.user_data.role == Role.TEACHER:
        if context.chat_data["mode"] == ChatMode.REVIEW:
            await query.delete_message()
            await MessageSender.ask_review(update, context)
            return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

        await CQReplySender.ask_class_communication_languages(context, query)
        return State.ASK_TEACHING_EXPERIENCE

    context.user_data.levels_for_teaching_language[data] = []

    # If this is a student that has chosen English, we don't ask them for their level
    # (it will be assessed) - only for their ability to read in English.
    # The question about the ability to read is not asked for languages other than English.
    if context.user_data.role == Role.STUDENT and data == "en":
        await CQReplySender.ask_yes_no(
            context,
            query,
            question_phrase_internal_id="ask_student_if_can_read_in_english",
        )
        return State.ASK_LEVEL_OR_COMMUNICATION_LANGUAGE

    await CQReplySender.ask_language_levels(context, query, show_done_button=False)
    return State.ASK_LEVEL_OR_COMMUNICATION_LANGUAGE


async def store_data_ask_another_level_or_communication_language_or_start_assessment(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores data, asks another level of the language or communication language or starts test.

    Stores data:

    * for students that want to learn English, data is their ability to read in English.
    * for students that want to learn other languages or for teachers, data is the level of
      the chosen language.

    Asks:

    * asks teacher for another level of this teaching language
    * asks students aged 5-12 that want to learn English about communication language, mark that
      they need oral interview
    * asks students aged 13-17 that want to learn English how long they've been learning
    * for adult students that want to learn English, start assessment
    * asks students of other ages that want to learn English about communication language
    * asks students that want to learn other languages about communication language in groups
    """

    query, data = await answer_callback_query_and_get_data(update)

    if data == CallbackData.DONE:
        # A teacher has finished selecting levels for this language: ask for another language
        await CQReplySender.ask_teaching_languages(context, query)
        return State.ASK_LEVEL_OR_ANOTHER_TEACHING_LANGUAGE_OR_COMMUNICATION_LANGUAGE

    user_data = context.user_data
    last_language_added = tuple(user_data.levels_for_teaching_language.keys())[-1]
    role = user_data.role

    # If this is a student that had chosen English, query.data is their ability to read in English.
    if role == Role.STUDENT and last_language_added == "en":
        user_data.student_can_read_in_english = True if data == CallbackData.YES else False

        can_read = user_data.student_can_read_in_english
        logger.info(f"User can read in English: {can_read}")

        if can_read and user_data.student_age_to <= 12:
            # young students: mark as requiring interview, ask about communication language
            user_data.student_needs_oral_interview = True
            await CQReplySender.ask_class_communication_languages(context, query)
            return State.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW

        if can_read and user_data.student_age_to < 18:
            # students of age 13 through 17 are asked how long they have been learning English
            await CQReplySender.ask_how_long_been_learning_english(context, query)
            return State.ADOLESCENTS_ASK_COMMUNICATION_LANGUAGE_OR_START_ASSESSMENT

        if can_read and user_data.student_age_from >= 18:
            # adult students: start assessment
            await prepare_assessment(context, query)
            return State.ASK_ASSESSMENT_QUESTION

        # if a student can NOT read in English: no assessment.  Adult students get A0...
        if user_data.student_age_from >= 18:
            user_data.levels_for_teaching_language["en"] = ["A0"]
        else:
            # ...while young students get no level and are marked to require oral interview.
            user_data.student_needs_oral_interview = True

        await CQReplySender.ask_class_communication_languages(context, query)
        return State.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW

    # If this is a teacher or a student that had chosen another language than English,
    # query.data is language level.
    user_data.levels_for_teaching_language[last_language_added].append(data)

    logger.info(user_data.levels_for_teaching_language)

    # Students can only choose one language and one level
    if role == Role.STUDENT:
        if context.chat_data["mode"] == ChatMode.REVIEW:
            await query.delete_message()
            await MessageSender.ask_review(update, context)
            return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

        await CQReplySender.ask_class_communication_languages(
            context,
            query,
        )
        return State.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW

    # Teacher can choose another level of the same language
    await CQReplySender.ask_language_levels(context, query)
    return State.ASK_LEVEL_OR_COMMUNICATION_LANGUAGE


async def store_non_teaching_help_ask_another_or_additional_help(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    query, data = await answer_callback_query_and_get_data(update)

    # protection against coding error
    if data not in NON_TEACHING_HELP_TYPES + (CallbackData.DONE,):
        raise ValueError(f"{data} cannot be in callback data for non-teaching help types.")

    # pressed "Done" or chose all types of help
    if data == CallbackData.DONE or len(context.user_data.non_teaching_help_types) == len(
        NON_TEACHING_HELP_TYPES
    ):
        if context.user_data.role == Role.STUDENT:
            await MessageSender.ask_review(update, context)
            return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT
        else:
            await CQReplySender.ask_teacher_peer_help(context, query)
            return State.PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP

    context.user_data.non_teaching_help_types.append(data)
    await CQReplySender.ask_non_teaching_help(context, query)
    return State.NON_TEACHING_HELP_MENU_OR_PEER_HELP_FOR_TEACHER_OR_REVIEW_FOR_STUDENT


async def check_if_review_needed_give_review_menu_or_ask_final_comment(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If the user requested a review, gives a review menu. Otherwise, asks for final comment."""
    query, data = await answer_callback_query_and_get_data(update)

    if data == CallbackData.YES:
        context.chat_data["mode"] = ChatMode.NORMAL  # set explicitly to normal just in case
        # I don't want to do edit_message_text. Let user info remain in the chat for user to see.
        await update.effective_chat.send_message(
            PHRASES["ask_final_comment"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return State.BYE
    else:
        # Switch into review mode to let other callbacks know that they should return user
        # back to the review callback instead of moving him normally along the conversation line
        context.chat_data["mode"] = ChatMode.REVIEW
        await CQReplySender.ask_review_category(context, query)
        return State.REVIEW_REQUESTED_ITEM


async def review_requested_item(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Reads callback data, asks corresponding question about the item they want to review,
    redirects to the corresponding state of the conversation (the state right after the moment when
    this question was asked in normal conversation flow).

    Note: since chat is in review mode now, the user will return straight back to review menu after
    they give amended information "upstream" in the conversation.
    """
    query, data = await answer_callback_query_and_get_data(update)

    locale = context.user_data.locale

    if data == UserDataReviewCategory.FIRST_NAME:
        await query.edit_message_text(
            PHRASES["ask_first_name"][locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        # Return state that is right after asking for the first name.
        # This state corresponds to the callback where the first name is stored.
        # This callback contains a check for a chat mode and will return the user
        # back to the review if chat is in review mode.
        # Same for other cases below.
        return State.ASK_LAST_NAME
    elif data == UserDataReviewCategory.LAST_NAME:
        await query.edit_message_text(
            PHRASES["ask_last_name"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return State.ASK_SOURCE
    elif data == UserDataReviewCategory.PHONE_NUMBER:
        # no need to check user_data here since the user couldn't have selected this option
        # if it wasn't there.
        # edit_message_text not possible here because of a button for sharing phone number
        await MessageSender.ask_phone_number(update, context)
        return State.ASK_EMAIL
    elif data == UserDataReviewCategory.EMAIL:
        await query.edit_message_text(
            PHRASES["ask_email"][locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return State.ASK_ROLE
    elif data == UserDataReviewCategory.TIMEZONE:
        await CQReplySender.ask_timezone(context, query)
        return State.TIME_SLOTS_START
    elif data == UserDataReviewCategory.AVAILABILITY:
        # set day of week to Monday to start asking about slots for each day
        context.chat_data["day_idx"] = 0
        context.user_data.time_slots_for_day = defaultdict(list)
        await CQReplySender.ask_time_slot(context, query)
        return State.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE
    elif data == UserDataReviewCategory.LANGUAGE_AND_LEVEL:
        context.user_data.levels_for_teaching_language = {}
        show_done_button = True if context.user_data.levels_for_teaching_language else False
        await CQReplySender.ask_teaching_languages(
            context, query, show_done_button=show_done_button
        )
        return State.ASK_LEVEL_OR_ANOTHER_TEACHING_LANGUAGE_OR_COMMUNICATION_LANGUAGE
    elif data == UserDataReviewCategory.CLASS_COMMUNICATION_LANGUAGE:
        await CQReplySender.ask_class_communication_languages(context, query)
        return State.ASK_TEACHING_EXPERIENCE  # FIXME check
    elif data == UserDataReviewCategory.STUDENT_AGE_GROUP:
        if context.user_data.role == Role.STUDENT:
            await CQReplySender.ask_student_age(context, query)
            return State.ASK_TIMEZONE
        await CQReplySender.ask_teacher_age_groups_of_students(context, query)
        return State.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP
    else:
        raise NotImplementedError(f"Cannot handle review of {data}")


async def store_additional_help_comment_ask_final_comment(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """For young teachers: stores comment on additional help, asks for final comment."""
    if update.message is None:
        return State.ASK_FINAL_COMMENT
    locale = context.user_data.locale

    context.user_data.teacher_additional_skills_comment = update.message.text

    # We want to give the young teacher the opportunity to double-check their email
    # without starting a full-fledged review
    await update.message.reply_text(
        f"{PHRASES['young_teacher_we_will_email_you'][locale]} {context.user_data.email}\n\n"
        f"{PHRASES['ask_final_comment'][locale]}"
    )
    return State.BYE


async def store_comment_end_conversation(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores comment and ends the conversation.

    For a would-be teacher that is under 18, stores their comment about potential useful skills.
    For others, stores the general comment. Ends the conversation."""
    data = context.user_data
    locale = data.locale

    if data.role == Role.TEACHER and data.teacher_is_under_18 is True:
        data.teacher_additional_skills_comment = update.message.text
    else:
        data.comment = update.message.text

    # number of groups is None for young teachers and 0 for adults that only want speaking club
    if data.role == Role.TEACHER and not data.teacher_number_of_groups:
        phrase_id = "bye_wait_for_message_from_coordinator"
    elif data.role == Role.STUDENT and data.student_needs_oral_interview is True:
        phrase_id = "bye_go_to_chat_with_coordinator"
    else:
        phrase_id = "bye_wait_for_message_from_bot"

    await update.effective_chat.send_message(PHRASES[phrase_id][locale])
    return ConversationHandler.END


async def cancel(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Cancels and ends the conversation."""

    user = update.message.from_user

    logger.info("User %s canceled the conversation.", user.first_name)

    # the /cancel command could come even before the user chooses the locale
    if context.user_data.locale:
        locale = context.user_data.locale
    else:
        locale = update.effective_user.language_code

    await update.message.reply_text(
        PHRASES["bye_cancel"][locale], reply_markup=InlineKeyboardMarkup([])
    )

    return ConversationHandler.END


async def send_help(update: Update, context: CUSTOM_CONTEXT_TYPES):
    """Displays help message."""

    await update.message.reply_text(
        "Enter /start to start the conversation!", reply_markup=ReplyKeyboardRemove()
    )
