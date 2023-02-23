import logging
import os
import re
from collections import defaultdict
from enum import IntEnum, auto

from telegram import (
    BotCommandScopeAllPrivateChats,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    MenuButtonCommands,
    ReplyKeyboardMarkup,
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

from samanthas_telegram_bot.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.constants import (
    DAY_OF_WEEK_FOR_INDEX,
    EMAIL_PATTERN,
    LOCALES,
    PHONE_PATTERN,
    PHRASES,
    STUDENT_AGE_GROUPS_FOR_TEACHER,
    CallbackData,
    Role,
)
from samanthas_telegram_bot.custom_context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.user_data import UserData

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# TODO menu!


class State(IntEnum):
    """Provides integer keys for the dictionary of states for ConversationHandler."""

    IS_REGISTERED = auto()
    ASK_FIRST_NAME_OR_BYE = auto()
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
    ASK_TEACHING_EXPERIENCE = auto()
    ASK_NUMBER_OF_GROUPS_OR_TEACHING_FREQUENCY = auto()
    ASK_TEACHING_FREQUENCY = auto()
    PREFERRED_STUDENT_AGE_GROUPS_START = auto()
    PREFERRED_STUDENT_AGE_GROUPS_MENU = auto()
    ASK_ADDITIONAL_SKILLS = auto()
    BYE = auto()


async def start(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Starts the conversation and asks the user about the language they want to communicate in."""

    logger.info(f"Chat ID: {update.effective_chat.id}")

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

    return State.ASK_FIRST_NAME_OR_BYE


async def redirect_to_coordinator_if_registered_ask_first_name(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If user is already registered, redirect to coordinator. Otherwise, ask for first name."""

    query = update.callback_query
    await query.answer()

    if query.data == CallbackData.YES:
        await query.edit_message_text(
            PHRASES["reply_go_to_other_chat"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return ConversationHandler.END

    await query.edit_message_text(
        # the message is the same for it to look like an interactive menu
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

    await update.message.reply_text(PHRASES["ask_last_name"][context.user_data.locale])
    return State.ASK_SOURCE


async def store_last_name_ask_source(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the last name and asks the user how they found out about Samantha's Group."""

    if update.message is None:
        return State.ASK_SOURCE

    context.user_data.last_name = update.message.text
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
        context.user_data.username = username
        logger.info(f"Username: {username}. Will be stored in the database.")
        await query.edit_message_text(
            PHRASES["ask_email"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return State.ASK_ROLE

    context.user_data.username = None
    await query.delete_message()

    await update.effective_chat.send_message(
        PHRASES["ask_phone"][context.user_data.locale],
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardMarkup(
            [
                [
                    KeyboardButton(
                        text=PHRASES["share_phone"][context.user_data.locale], request_contact=True
                    )
                ]
            ]
        ),
    )

    return State.ASK_EMAIL


async def store_phone_ask_email(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the phone number and asks for email."""

    if update.message is None:
        return State.ASK_EMAIL

    # just in case: deleting spaces and hyphens
    text = (
        update.message.text.replace("-", "").replace(" ", "").strip()
        if update.message.text
        else ""
    )

    if not (update.message.contact or PHONE_PATTERN.match(text)):
        await update.message.reply_text(
            PHRASES["invalid_phone_number"][context.user_data.locale],
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.ASK_EMAIL

    if update.message.contact:
        context.user_data.phone_number = update.message.contact.phone_number
    else:
        context.user_data.phone_number = text

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
        context.user_data.time_slots_for_day = defaultdict(list)

        # setting day of week to Monday.  This is temporary, so won't mix it with user_data
        context.chat_data["day_idx"] = 0

    elif query.data == CallbackData.NEXT:  # user pressed "next" button after choosing slots
        if context.chat_data["day_idx"] == 6:  # we have reached Sunday
            logger.info(context.user_data.time_slots_for_day)
            # TODO what if the user chose no slots at all?
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
        await CQReplySender.ask_student_communication_languages(context, query)
        return State.ASK_TEACHING_EXPERIENCE

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
        await CQReplySender.ask_student_communication_languages(
            context,
            query,
        )
        return State.ASK_TEACHING_EXPERIENCE

    # Ask the teacher for another level of the same language
    await CQReplySender.ask_language_levels(context, query)
    return State.ASK_LEVEL_OR_COMMUNICATION_LANGUAGE


async def store_student_communication_language_start_test_or_ask_teaching_experience(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores communication language, starts test for a student (if the teaching language
    chosen was English) or asks teacher about teaching experience.
    """

    query = update.callback_query
    await query.answer()

    context.user_data.communication_language_in_class = query.data

    logger.info(context.user_data.communication_language_in_class)

    if context.user_data.role == Role.STUDENT:
        # start test
        return State.BYE  # TODO
    else:
        await CQReplySender.ask_yes_no(
            context, query, question_phrase_internal_id="ask_teacher_experience"
        )
        return State.ASK_NUMBER_OF_GROUPS_OR_TEACHING_FREQUENCY


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

    return State.PREFERRED_STUDENT_AGE_GROUPS_MENU


async def store_student_age_group_ask_another(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores preferred age group of students, asks another."""
    query = update.callback_query
    await query.answer()

    if query.data == CallbackData.DONE:
        return State.BYE  # TODO

    context.user_data.teacher_age_groups_of_students.append(query.data)

    if len(context.user_data.teacher_age_groups_of_students) == len(
        STUDENT_AGE_GROUPS_FOR_TEACHER
    ):
        return State.BYE  # TODO

    await CQReplySender.ask_student_age_groups_for_teacher(context, query)

    return State.PREFERRED_STUDENT_AGE_GROUPS_MENU


async def bye(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
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

    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
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
            State.ASK_FIRST_NAME_OR_BYE: [
                CallbackQueryHandler(redirect_to_coordinator_if_registered_ask_first_name)
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
            State.ASK_TEACHING_EXPERIENCE: [
                CallbackQueryHandler(
                    store_student_communication_language_start_test_or_ask_teaching_experience
                )
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
            State.PREFERRED_STUDENT_AGE_GROUPS_MENU: [
                CallbackQueryHandler(store_student_age_group_ask_another)
            ],
            State.BYE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bye)],
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
