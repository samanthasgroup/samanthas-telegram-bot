import logging
import os
import re
from collections import defaultdict
from enum import IntEnum, auto

import phonenumbers  # TODO 00
from telegram import (
    BotCommandScopeAllPrivateChats,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonCommands,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from samanthas_telegram_bot.api_queries import chat_id_is_registered
from samanthas_telegram_bot.assessment import get_questions
from samanthas_telegram_bot.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.constants import (
    DAY_OF_WEEK_FOR_INDEX,
    EMAIL_PATTERN,
    LOCALES,
    PHRASES,
    STUDENT_AGE_GROUPS_FOR_TEACHER,
    CallbackData,
    ChatMode,
    Role,
    UserDataReviewCategory,
)
from samanthas_telegram_bot.custom_context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.send_message import (
    send_message_for_phone_number,
    send_message_for_reviewing_user_data,
)
from samanthas_telegram_bot.user_data import UserData

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class State(IntEnum):
    """Provides integer keys for the dictionary of states for ConversationHandler."""

    IS_REGISTERED = auto()
    CHECK_CHAT_ID_ASK_FIRST_NAME = auto()
    CHECK_IF_WANTS_TO_REGISTER_ANOTHER_PERSON_ASK_FIRST_NAME = auto()
    ASK_LAST_NAME = auto()
    ASK_SOURCE = auto()
    CHECK_USERNAME = auto()
    ASK_PHONE_NUMBER = auto()
    ASK_EMAIL = auto()
    ASK_ROLE = auto()
    ASK_AGE = auto()
    ASK_TIMEZONE = auto()
    TIME_SLOTS_START = auto()
    TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE = auto()
    ASK_LEVEL_OR_ANOTHER_TEACHING_LANGUAGE_OR_COMMUNICATION_LANGUAGE = auto()
    ASK_LEVEL_OR_COMMUNICATION_LANGUAGE = auto()
    ASK_TEACHING_EXPERIENCE_OR_START_ASSESSMENT = auto()
    ASK_ASSESSMENT_QUESTION = auto()
    ASK_NUMBER_OF_GROUPS_OR_TEACHING_FREQUENCY = auto()
    ASK_TEACHING_FREQUENCY = auto()
    PREFERRED_STUDENT_AGE_GROUPS_START = auto()
    PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_HELP_FOR_STUDENTS = auto()
    ASK_PEER_HELP_OR_ADDITIONAL_HELP = auto()
    PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP = auto()
    ASK_REVIEW = auto()
    REVIEW_MENU_OR_ASK_FINAL_COMMENT = auto()
    REVIEW_REQUESTED_ITEM = auto()
    BYE = auto()


async def start(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Starts the conversation and asks the user about the language they want to communicate in."""

    # TODO if user clears the history after starting, they won't be able to start until they cancel
    logger.info(f"Chat ID: {update.effective_chat.id}")

    context.chat_data["mode"] = ChatMode.NORMAL

    await update.effective_chat.set_menu_button(MenuButtonCommands())

    context.user_data.days = []
    context.user_data.time = []

    greeting = ""
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


async def store_interface_lang_ask_if_already_registered(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores the interface language and asks the user if they are already registered."""

    query = update.callback_query
    await query.answer()
    context.user_data.locale = query.data

    await CQReplySender.ask_yes_no(
        context,
        query,
        question_phrase_internal_id="ask_already_with_us",
    )

    return State.CHECK_CHAT_ID_ASK_FIRST_NAME


async def redirect_to_coordinator_if_registered_check_chat_id_ask_first_name(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Checks user's answer if they are registered, checks chat ID, asks for first name,

    If user is already registered (as per their answer), redirects to coordinator.
    Otherwise, checks if Telegram chat ID is already present in the back end.
    If it is, asks the user if they still want to proceed with registration.

    If the user said they were not registered and chat ID was not found,
    asks for first name.
    """

    query = update.callback_query
    await query.answer()

    if query.data == CallbackData.YES:
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

    query = update.callback_query
    await query.answer()

    if query.data == CallbackData.NO:
        await query.edit_message_text(
            PHRASES["bye_wait_for_message"][context.user_data.locale],
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
        await send_message_for_reviewing_user_data(update, context)
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
        await send_message_for_reviewing_user_data(update, context)
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

    username = update.effective_user.username

    if username:
        await update.effective_chat.send_message(
            f"{PHRASES['ask_username_1'][context.user_data.locale]} @{username}"
            f"{PHRASES['ask_username_2'][context.user_data.locale]}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=PHRASES[f"username_reply_{option}"][context.user_data.locale],
                            callback_data=f"store_username_{option}",
                        )
                        for option in (CallbackData.YES, CallbackData.NO)
                    ],
                ]
            ),
        )

    return State.ASK_PHONE_NUMBER


async def store_username_if_available_ask_phone_or_email(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If user's username was empty or they chose to provide a phone number, ask for it.
    If the user provides their username, ask their email (jump over one function).
    """

    username = update.effective_user.username

    query = update.callback_query
    await query.answer()

    if query.data == "store_username_yes" and username:
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

    await send_message_for_phone_number(update, context)
    return State.ASK_EMAIL


async def store_phone_ask_email(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the phone number and asks for email."""

    if update.message is None:
        return State.ASK_EMAIL

    # 1. Read phone number
    phone_number_to_parse = (
        update.message.contact.phone_number if update.message.contact else update.message.text
    )

    # 2. Parse phone number
    try:
        parsed_phone_number = phonenumbers.parse(phone_number_to_parse)
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
        await send_message_for_reviewing_user_data(update, context)
        return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    await update.message.reply_text(
        PHRASES["ask_email"][context.user_data.locale],
        reply_markup=ReplyKeyboardRemove(),
    )
    logger.info(f"Phone: {context.user_data.phone_number}")
    return State.ASK_ROLE


async def store_email_ask_role(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the email and asks whether the user wants to be a student or a teacher."""

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

    if context.chat_data["mode"] == ChatMode.REVIEW:
        await update.message.delete()
        await send_message_for_reviewing_user_data(update, context)
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

    query = update.callback_query
    await query.answer()

    context.user_data.role = query.data

    if context.user_data.role == Role.TEACHER:
        await CQReplySender.ask_yes_no(
            context,
            query,
            question_phrase_internal_id="ask_if_18",
        )
    else:
        student_ages = [
            ["6-8", "9-11", "12-14", "15-17"],
            ["18-20", "21-25", "26-30", "31-35"],
            ["36-40", "41-45", "46-50", "51-55"],
            ["56-60", "61-65", "66-70", "71-75"],
            ["76-80", "81-65", "86-90", "91-95"],
        ]

        rows_of_buttons = [
            [InlineKeyboardButton(text, callback_data=text) for text in row]
            for row in student_ages
        ]

        await query.edit_message_text(
            PHRASES["ask_age"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup(rows_of_buttons),
        )

    return State.ASK_TIMEZONE


async def store_age_ask_timezone(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """If user is a teacher under 18, informs that teachers under 18 are not allowed
    and asks about additional skills. Otherwise, stores age range (for students) and asks timezone.
    """

    query = update.callback_query
    await query.answer()

    # end conversation for would-be teachers that are minors
    if context.user_data.role == Role.TEACHER:
        if query.data == CallbackData.YES:
            context.user_data.teacher_is_under_18 = False
        else:
            context.user_data.teacher_is_under_18 = True
            await query.edit_message_text(
                PHRASES["reply_under_18"][context.user_data.locale],
                reply_markup=InlineKeyboardMarkup([]),
            )
            return State.BYE

    if context.user_data.role == Role.STUDENT:
        context.user_data.age = query.data

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
    await query.answer()

    if re.match(r"^[+-]?\d{1,2}$", query.data):  # this is a UTC offset
        context.user_data.utc_offset = int(query.data)

        if context.chat_data["mode"] == ChatMode.REVIEW:
            await query.delete_message()
            await send_message_for_reviewing_user_data(update, context)
            return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

        context.user_data.time_slots_for_day = defaultdict(list)

        # set day of week to Monday to start asking about slots for each day
        context.chat_data["day_idx"] = 0

    elif query.data == CallbackData.NEXT:  # user pressed "next" button after choosing slots
        if context.chat_data["day_idx"] == 6:  # we have reached Sunday
            logger.info(context.user_data.time_slots_for_day)
            # TODO what if the user chose no slots at all?

            if context.chat_data["mode"] == ChatMode.REVIEW:
                await query.delete_message()
                await send_message_for_reviewing_user_data(update, context)
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

    await CQReplySender.ask_time_slot(context, query)

    return State.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE


async def store_one_time_slot_ask_another(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores one time slot and offers to choose another."""
    query = update.callback_query
    await query.answer()

    day = DAY_OF_WEEK_FOR_INDEX[context.chat_data["day_idx"]]
    context.user_data.time_slots_for_day[day].append(query.data)

    await CQReplySender.ask_time_slot(context, query)

    return State.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE


async def store_teaching_language_ask_another_or_level_or_communication_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores teaching language, asks for level. If the user is a teacher and is done choosing
    levels, offers to choose another language.

    If the user is a teacher and has finished choosing languages, asks about language of
    communication in class.
    """

    query = update.callback_query
    await query.answer()

    # for now students can only choose one language, so callback_data == "done" is only possible
    # for a teacher, but we'll keep it explicit here
    if query.data == CallbackData.DONE and context.user_data.role == Role.TEACHER:
        if context.chat_data["mode"] == ChatMode.REVIEW:
            await query.delete_message()
            await send_message_for_reviewing_user_data(update, context)
            return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

        await CQReplySender.ask_class_communication_languages(context, query)
        return State.ASK_TEACHING_EXPERIENCE_OR_START_ASSESSMENT

    context.user_data.levels_for_teaching_language[query.data] = []

    await CQReplySender.ask_language_levels(context, query, show_done_button=False)
    return State.ASK_LEVEL_OR_COMMUNICATION_LANGUAGE


async def store_level_ask_level_for_next_language_or_communication_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores level, asks for another level of the language chosen (for teachers) or for
    communication language in groups (for students).
    """

    query = update.callback_query
    await query.answer()

    if query.data == CallbackData.DONE:
        # A teacher has finished selecting levels for this language: ask for another language
        await CQReplySender.ask_teaching_languages(context, query)
        return State.ASK_LEVEL_OR_ANOTHER_TEACHING_LANGUAGE_OR_COMMUNICATION_LANGUAGE

    last_language_added = tuple(context.user_data.levels_for_teaching_language.keys())[-1]
    context.user_data.levels_for_teaching_language[last_language_added].append(query.data)

    logger.info(context.user_data.levels_for_teaching_language)

    # move on for a student (they can only choose one language and one level)
    if context.user_data.role == Role.STUDENT:
        if context.chat_data["mode"] == ChatMode.REVIEW:
            await query.delete_message()
            await send_message_for_reviewing_user_data(update, context)
            return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

        await CQReplySender.ask_class_communication_languages(
            context,
            query,
        )
        return State.ASK_TEACHING_EXPERIENCE_OR_START_ASSESSMENT

    # Ask the teacher for another level of the same language
    await CQReplySender.ask_language_levels(context, query)
    return State.ASK_LEVEL_OR_COMMUNICATION_LANGUAGE


async def store_class_communication_language_start_test_or_ask_teaching_experience(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores communication language, starts test for a student (if the teaching language
    chosen was English) or asks teacher about teaching experience.
    """

    query = update.callback_query
    await query.answer()

    context.user_data.communication_language_in_class = query.data

    if context.chat_data["mode"] == ChatMode.REVIEW:
        await query.delete_message()
        await send_message_for_reviewing_user_data(update, context)
        return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    logger.info(context.user_data.communication_language_in_class)

    locale = context.user_data.locale

    if context.user_data.role == Role.STUDENT:
        # prepare questions and set index to 0
        context.chat_data["assessment_questions"] = get_questions("en", "A1")  # TODO for now
        context.chat_data["current_question_idx"] = 0

        # TODO start test instead of asking for final comment, make sure student gets to review too
        await query.edit_message_text(
            PHRASES["ask_student_start_assessment"][locale],
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=PHRASES["assessment_option_start"][locale],
                            callback_data=CallbackData.OK,
                        )
                    ]
                ]
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return State.ASK_ASSESSMENT_QUESTION
    else:
        await CQReplySender.ask_yes_no(
            context, query, question_phrase_internal_id="ask_teacher_experience"
        )
        return State.ASK_NUMBER_OF_GROUPS_OR_TEACHING_FREQUENCY


async def assessment_store_answer_ask_question(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores answer to the question (unless this is the beginning of the test), asks next one."""

    query = update.callback_query
    await query.answer()

    data = query.data
    # TODO store number of correct answers? How to determine level?

    if (
        context.chat_data["current_question_idx"]
        == len(context.chat_data["assessment_questions"]) - 1
    ):
        # TODO store and send message
        return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    if data in ("1", "2", "3", "4", CallbackData.DONT_KNOW):
        # TODO store
        context.chat_data["current_question_idx"] += 1

    await CQReplySender.asks_next_assessment_question(context, query)
    return State.ASK_ASSESSMENT_QUESTION


async def store_prior_teaching_experience_ask_groups_or_frequency(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores information about teaching experience, asks for frequency (inexperienced teachers)
    or number of groups (for experienced teachers).
    """

    query = update.callback_query
    await query.answer()
    context.user_data.teacher_has_prior_experience = (
        True if query.data == CallbackData.YES else False
    )

    logger.info(f"Has teaching experience: {context.user_data.teacher_has_prior_experience}")

    if context.user_data.teacher_has_prior_experience:
        numbers_of_groups = (1, 2)

        buttons = [
            [
                InlineKeyboardButton(
                    PHRASES[f"option_number_of_groups_{number}"][context.user_data.locale],
                    callback_data=number,
                )
                for number in numbers_of_groups
            ]
        ]

        await query.edit_message_text(
            PHRASES["ask_teacher_number_of_groups"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return State.ASK_TEACHING_FREQUENCY
    else:
        await CQReplySender.ask_teaching_frequency(context, query)
        return State.PREFERRED_STUDENT_AGE_GROUPS_START


async def store_number_of_groups_ask_frequency(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """For experienced teachers: stores information about number of groups, asks for frequency
    (inexperienced teachers).
    """
    query = update.callback_query
    await query.answer()

    context.user_data.teacher_number_of_groups = query.data

    await CQReplySender.ask_teaching_frequency(context, query)
    return State.PREFERRED_STUDENT_AGE_GROUPS_START


async def store_frequency_ask_student_age_groups(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores frequency, asks for preferred age groups of students."""
    query = update.callback_query
    await query.answer()

    context.user_data.teacher_class_frequency = query.data
    context.user_data.teacher_age_groups_of_students = []

    await CQReplySender.ask_student_age_groups_for_teacher(context, query)

    return State.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_HELP_FOR_STUDENTS


async def store_student_age_group_ask_another_or_help_for_students(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores preferred age group of students, asks another.  If the teacher is done, ask about
    additional help for students.
    """
    query = update.callback_query
    await query.answer()

    if query.data != CallbackData.DONE:
        context.user_data.teacher_age_groups_of_students.append(query.data)

    # teacher pressed "Done" or chose all age groups
    if query.data == CallbackData.DONE or len(
        context.user_data.teacher_age_groups_of_students
    ) == len(STUDENT_AGE_GROUPS_FOR_TEACHER):
        await CQReplySender.ask_teacher_about_help_with_cv_and_speaking_clubs(context, query)
        return State.ASK_PEER_HELP_OR_ADDITIONAL_HELP

    await CQReplySender.ask_student_age_groups_for_teacher(context, query)
    return State.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_HELP_FOR_STUDENTS


async def store_help_for_students_ask_peer_help_or_additional_help(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores information about additional help for students. If the teacher has teaching
    experience, asks about help for less experienced teachers. Otherwise, asks about any other
    types of help the teacher could provide (for more experienced teachers, this question will be
    asked at the next stage).
    """
    query = update.callback_query
    await query.answer()

    # callback_data "cv_and_speaking_club" will lead to both attributes being True.
    # I am not extracting constants to point out that these exact words are present in CSV file
    # with phrases (where constants are obviously impossible),
    if "cv" in query.data:
        context.user_data.teacher_can_help_with_cv = True
    if "speaking_club" in query.data:
        context.user_data.teacher_can_help_with_speaking_club = True

    if context.user_data.teacher_has_prior_experience is True:
        # I will be storing the selected options in boolean flags of TeacherPeerHelp(),
        # but in order to remove selected options from InlineKeyboard, I have to store exact
        # callback_data somewhere.
        context.chat_data["peer_help_callback_data"] = set()
        await CQReplySender.ask_teacher_peer_help(context, query)
        return State.PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP

    await query.edit_message_text(
        PHRASES["ask_teacher_any_additional_help"][context.user_data.locale],
        reply_markup=InlineKeyboardMarkup([]),
    )
    return State.ASK_REVIEW


async def store_peer_help_ask_another_or_additional_help(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores one option of teacher peer help, asks for another.  If the teacher is done,
    asks for any additional help (in free text)."""
    query = update.callback_query
    await query.answer()

    if query.data == CallbackData.DONE:
        await query.edit_message_text(
            PHRASES["ask_teacher_any_additional_help"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return State.ASK_REVIEW

    if query.data == "consult":
        context.user_data.teacher_peer_help.can_consult_other_teachers = True
    elif query.data == "children_group":
        context.user_data.teacher_peer_help.can_help_with_children_group = True
    elif query.data == "materials":
        context.user_data.teacher_peer_help.can_help_with_materials = True
    elif query.data == "check_syllabus":
        context.user_data.teacher_peer_help.can_check_syllabus = True
    elif query.data == "feedback":
        context.user_data.teacher_peer_help.can_give_feedback = True
    elif query.data == "invite":
        context.user_data.teacher_peer_help.can_invite_to_class = True
    elif query.data == "tandem":
        context.user_data.teacher_peer_help.can_work_in_tandem = True

    # to remove this button from the keyboard
    context.chat_data["peer_help_callback_data"].add(query.data)
    await CQReplySender.ask_teacher_peer_help(context, query)
    return State.PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP


async def store_teachers_additional_skills_ask_if_review_needed(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores teacher's additional skills and asks to review main user data."""
    if update.message is None:
        return State.ASK_REVIEW

    if context.user_data.role == Role.TEACHER:
        context.user_data.teacher_additional_skills_comment = update.message.text

    await send_message_for_reviewing_user_data(update, context)
    return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT


async def check_if_review_needed_give_review_menu_or_ask_final_comment(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If the user requested a review, gives a review menu. Otherwise, asks for final comment."""
    query = update.callback_query
    await query.answer()

    if query.data == CallbackData.YES:
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
    query = update.callback_query
    await query.answer()

    data = query.data
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
        await send_message_for_phone_number(update, context)
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
        return State.ASK_TEACHING_EXPERIENCE_OR_START_ASSESSMENT
    else:
        raise NotImplementedError(f"Cannot handle review of {data}")


async def store_comment_end_conversation(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """For a would-be teacher that is under 18, store their comment about potential useful skills.
    For others, store the general comment. End the conversation."""
    locale = context.user_data.locale

    if context.user_data.role == Role.TEACHER and context.user_data.teacher_is_under_18 is True:
        context.user_data.teacher_additional_skills_comment = update.message.text
        await update.effective_chat.send_message(PHRASES["bye_teacher_under_18"][locale])
    else:
        context.user_data.comment = update.message.text
        await update.effective_chat.send_message(PHRASES["bye_wait_for_message"][locale])

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


async def post_init(application: Application):
    await application.bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())
    await application.bot.set_my_commands(
        [
            ("start", "Start registration"),
            ("cancel", "Cancel registration process"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
        language_code="en",
    )
    await application.bot.set_my_commands(
        [
            ("start", "Начать регистрацию"),
            ("cancel", "Прервать процесс регистрации"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
        language_code="ru",
    )
    # TODO Ukrainian
    await application.bot.set_my_commands(
        [
            ("start", "Начать регистрацию"),
            ("cancel", "Прервать процесс регистрации"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
        language_code="ua",
    )


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it the bot's token.
    application = (
        Application.builder()
        .token(os.environ.get("TOKEN"))
        .context_types(ContextTypes(user_data=UserData))
        .post_init(post_init)
        .build()
    )

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            State.IS_REGISTERED: [
                CallbackQueryHandler(store_interface_lang_ask_if_already_registered)
            ],
            State.CHECK_CHAT_ID_ASK_FIRST_NAME: [
                CallbackQueryHandler(
                    redirect_to_coordinator_if_registered_check_chat_id_ask_first_name
                )
            ],
            State.CHECK_IF_WANTS_TO_REGISTER_ANOTHER_PERSON_ASK_FIRST_NAME: [
                CallbackQueryHandler(
                    say_bye_if_does_not_want_to_register_another_or_ask_first_name
                )
            ],
            State.ASK_LAST_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, store_first_name_ask_last_name)
            ],
            State.ASK_SOURCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, store_last_name_ask_source)
            ],
            State.CHECK_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, store_source_check_username)
            ],
            State.ASK_PHONE_NUMBER: [
                CallbackQueryHandler(store_username_if_available_ask_phone_or_email)
            ],
            State.ASK_EMAIL: [
                MessageHandler(
                    (filters.CONTACT ^ filters.TEXT) & ~filters.COMMAND, store_phone_ask_email
                )
            ],
            State.ASK_ROLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, store_email_ask_role)
            ],
            State.ASK_AGE: [CallbackQueryHandler(store_role_ask_age)],
            State.ASK_TIMEZONE: [CallbackQueryHandler(store_age_ask_timezone)],
            State.TIME_SLOTS_START: [
                CallbackQueryHandler(store_timezone_ask_slots_for_one_day_or_teaching_language)
            ],
            State.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE: [
                CallbackQueryHandler(
                    store_timezone_ask_slots_for_one_day_or_teaching_language, pattern="^next$"
                ),
                CallbackQueryHandler(store_one_time_slot_ask_another),
            ],
            State.ASK_LEVEL_OR_ANOTHER_TEACHING_LANGUAGE_OR_COMMUNICATION_LANGUAGE: [
                CallbackQueryHandler(
                    store_teaching_language_ask_another_or_level_or_communication_language
                ),
            ],
            State.ASK_LEVEL_OR_COMMUNICATION_LANGUAGE: [
                CallbackQueryHandler(
                    store_level_ask_level_for_next_language_or_communication_language
                )
            ],
            State.ASK_TEACHING_EXPERIENCE_OR_START_ASSESSMENT: [
                CallbackQueryHandler(
                    store_class_communication_language_start_test_or_ask_teaching_experience
                )
            ],
            State.ASK_ASSESSMENT_QUESTION: [
                CallbackQueryHandler(assessment_store_answer_ask_question)
            ],
            State.ASK_NUMBER_OF_GROUPS_OR_TEACHING_FREQUENCY: [
                CallbackQueryHandler(store_prior_teaching_experience_ask_groups_or_frequency)
            ],
            State.ASK_TEACHING_FREQUENCY: [
                CallbackQueryHandler(store_number_of_groups_ask_frequency)
            ],
            State.PREFERRED_STUDENT_AGE_GROUPS_START: [
                CallbackQueryHandler(store_frequency_ask_student_age_groups)
            ],
            State.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_HELP_FOR_STUDENTS: [
                CallbackQueryHandler(store_student_age_group_ask_another_or_help_for_students)
            ],
            State.ASK_PEER_HELP_OR_ADDITIONAL_HELP: [
                CallbackQueryHandler(store_help_for_students_ask_peer_help_or_additional_help)
            ],
            State.PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP: [
                CallbackQueryHandler(store_peer_help_ask_another_or_additional_help)
            ],
            State.ASK_REVIEW: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    store_teachers_additional_skills_ask_if_review_needed,
                )
            ],
            State.REVIEW_MENU_OR_ASK_FINAL_COMMENT: [
                CallbackQueryHandler(check_if_review_needed_give_review_menu_or_ask_final_comment)
            ],
            State.REVIEW_REQUESTED_ITEM: [CallbackQueryHandler(review_requested_item)],
            State.BYE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, store_comment_end_conversation)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    help_handler = CommandHandler("help", send_help)
    application.add_handler(help_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
