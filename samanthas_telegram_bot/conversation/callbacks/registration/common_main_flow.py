import asyncio
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

from samanthas_telegram_bot.api_clients import BackendClient, ChatwootClient, SmallTalkClient
from samanthas_telegram_bot.api_clients.auxil.constants import (
    PERSON_EXISTENCE_CHECK_INVALID_EMAIL_MESSAGE_FROM_BACKEND,
)
from samanthas_telegram_bot.api_clients.backend.exceptions import BackendClientError
from samanthas_telegram_bot.auxil.constants import (
    BOT_TECH_SUPPORT_USERNAME,
    EMAIL_PATTERN,
    RUSSIAN_DOMAINS,
)
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.conversation.auxil.enums import ConversationMode
from samanthas_telegram_bot.conversation.auxil.enums import ConversationStateCommon as CommonState
from samanthas_telegram_bot.conversation.auxil.enums import (
    ConversationStateCoordinator as CoordinatorState,
)
from samanthas_telegram_bot.conversation.auxil.enums import (
    ConversationStateStudent as StudentState,
)
from samanthas_telegram_bot.conversation.auxil.enums import (
    ConversationStateTeacherAdult as AdultTeacherState,
)
from samanthas_telegram_bot.conversation.auxil.enums import ConversationStateTeacherUnder18
from samanthas_telegram_bot.conversation.auxil.helpers import (
    answer_callback_query_and_get_data,
    notify_speaking_club_coordinator_about_high_level_student,
)
from samanthas_telegram_bot.conversation.auxil.message_sender import MessageSender
from samanthas_telegram_bot.data_structures.constants import (
    ENGLISH,
    LEVELS_TOO_HIGH,
    LOCALES,
    RUSSIAN,
    UKRAINIAN,
)
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import LoggingLevel, Role
from samanthas_telegram_bot.data_structures.literal_types import Locale


async def start(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Starts the conversation and asks the user about the interface language.

    The interface language may not match the interface language of the phone, so better to ask.
    """

    user_data = context.user_data

    user_data.clear_student_data()
    user_data.chat_id = update.effective_chat.id

    # This should not be needed in production, just adding as a precaution to avoid unexpected
    # side effects of changing contacts in Chatwoot and/or backend
    user_data.helpdesk_conversation_id = None

    await logs(
        bot=context.bot,
        text="Registration process started",
        update=update,
    )

    context.bot_data.conversation_mode_for_chat_id[
        context.user_data.chat_id
    ] = ConversationMode.REGISTRATION_MAIN_FLOW

    await update.effective_chat.set_menu_button(MenuButtonCommands())

    # Set the iterable attributes to empty lists/sets to avoid TypeError/KeyError later on.
    # Methods handling these iterables can be called from different callbacks, so better to set
    # them here, in one place.
    user_data.day_and_time_slot_ids = []
    user_data.language_and_level_ids = []
    user_data.levels_for_teaching_language = {}
    user_data.non_teaching_help_types = []
    user_data.teacher_student_age_range_ids = []

    # We will be storing the selected options in boolean flags of TeacherPeerHelp(),
    # but in order to remove selected options from InlineKeyboard, I have to store exact
    # callback_data somewhere.
    context.chat_data.peer_help_callback_data = set()

    # set day of week to Monday to start asking about slots for each day
    context.chat_data.day_index = 0

    greeting = "🚧 ТЕСТОВИЙ РЕЖИМ | TEST MODE 🚧\n\n"  # noqa # TODO remove going to production
    for locale in LOCALES:
        greeting += (
            rf"{context.bot_data.phrases['hello'][locale]} {update.message.from_user.first_name}! "
            f"{context.bot_data.phrases['choose_language_of_conversation'][locale]}\n\n"
        )

    await update.message.reply_text(
        greeting,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(text="українською", callback_data=UKRAINIAN)],
                [InlineKeyboardButton(text="in English", callback_data=ENGLISH)],
                [InlineKeyboardButton(text="по-русски", callback_data=RUSSIAN)],
            ]
        ),
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
        parse_mode=ParseMode.HTML,
    )

    return CommonState.SHOW_GDPR_DISCLAIMER


async def show_gdpr_disclaimer(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Show GDPR disclaimer to user. No data is stored here."""

    query, _ = await answer_callback_query_and_get_data(update)

    await CQReplySender.show_gdpr_disclaimer(context, query)

    return CommonState.CHECK_CHAT_ID_ASK_ROLE


async def redirect_registered_user_to_coordinator(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If user is already registered (as per their answer), redirects to coordinator."""
    query, _ = await answer_callback_query_and_get_data(update)

    locale: Locale = context.user_data.locale
    await query.edit_message_text(
        context.bot_data.phrases["reply_go_to_other_chat"][locale],
        reply_markup=InlineKeyboardMarkup([]),
    )
    return CommonState.CHAT_WITH_OPERATOR


async def check_chat_id_ask_role_if_id_does_not_exist(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Checks user's answer if they are registered, checks chat ID, asks role.

    Checks if Telegram chat ID is already present in the back end.
    If it is, asks the user if they still want to proceed with registration. Otherwise,
    asks their desired role (student, teacher).
    """
    query, data = await answer_callback_query_and_get_data(update)

    if await BackendClient.chat_id_is_registered(update, context):
        context.user_data.helpdesk_conversation_id = (
            await BackendClient.get_helpdesk_conversation_id(update, context)
        )
        await CQReplySender.ask_yes_no(
            context, query, question_phrase_internal_id="reply_chat_id_found"
        )
        return CommonState.ASK_ROLE_OR_BYE

    await CQReplySender.ask_role(context, query)
    return CommonState.SHOW_GENERAL_DISCLAIMER


async def say_bye_if_does_not_want_to_register_another_person(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If user does not want to register another person, says bye."""
    query, _ = await answer_callback_query_and_get_data(update)

    locale: Locale = context.user_data.locale
    await query.edit_message_text(
        context.bot_data.phrases["bye_wait_for_message_from_bot"][locale],
        reply_markup=InlineKeyboardMarkup([]),
    )
    return CommonState.CHAT_WITH_OPERATOR


async def ask_role(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Asks role. No data is stored here"""
    query, _ = await answer_callback_query_and_get_data(update)

    await CQReplySender.ask_role(context, query)
    return CommonState.SHOW_GENERAL_DISCLAIMER


async def store_role_show_general_disclaimer(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Store role, show general disclaimer."""
    query, context.user_data.role = await answer_callback_query_and_get_data(update)

    await CQReplySender.show_general_disclaimer(context, query)
    return CommonState.SHOW_LEGAL_DISCLAIMER_OR_ASK_FIRST_NAME_OR_BYE


async def show_legal_disclaimer_or_ask_first_name(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Show legal disclaimer to volunteers with locales other than ``ua``. Else, ask first name.

    No data is stored here.
    """
    query, _ = await answer_callback_query_and_get_data(update)
    user_data = context.user_data

    # Legal disclaimer is for non-Ukrainian coordinators and teachers only. Others skip to name.
    if user_data.role != Role.STUDENT and user_data.locale != "ua":
        await CQReplySender.show_legal_disclaimer(context, query)
        return CommonState.ASK_FIRST_NAME_OR_BYE

    await CQReplySender.ask_first_name(context, query)
    await MessageSender.send_info_on_reviewable_fields_if_applicable(update, context)
    return CommonState.ASK_LAST_NAME


async def say_bye_if_disclaimer_not_accepted(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Says goodbye to user that did not accept disclaimer."""
    query, _ = await answer_callback_query_and_get_data(update)

    await logs(
        bot=context.bot,
        text="User didn't accept one of disclaimers. Cancelling registration.",
        update=update,
    )
    locale: Locale = context.user_data.locale
    await query.edit_message_text(
        context.bot_data.phrases["bye_cancel"][locale],
        reply_markup=InlineKeyboardMarkup([]),
    )
    return ConversationHandler.END


async def ask_first_name(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Ask first name. No data is stored here.

    If this is main registration flow, show a note on some answers being editable during review.
    """
    query, _ = await answer_callback_query_and_get_data(update)

    await CQReplySender.ask_first_name(context, query)
    await MessageSender.send_info_on_reviewable_fields_if_applicable(update, context)

    return CommonState.ASK_LAST_NAME


async def store_first_name_ask_last_name(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int | None:
    """Stores the first name and asks the last name."""

    # It is better for less ambiguity to ask first name and last name in separate questions

    # It is impossible to send an empty message, but if for some reason user edits their previous
    # message, an update will be issued, but .message attribute will be none.
    # This will trigger an exception, although the bot won't stop working.  Still we don't want it.
    # So in this case just wait for user to type in the actual new message by returning him to the
    # same state again.
    # This can be potentially refactored, but unless more functionality is needed, it would result
    # in something like complex decorator, so not doing it yet.
    # TODO an enhancement could be to store the information from the edited message
    if update.message is None:
        return None

    context.user_data.first_name = update.message.text

    if (
        context.bot_data.conversation_mode_for_chat_id[context.user_data.chat_id]
        == ConversationMode.REGISTRATION_REVIEW
    ):
        await update.message.delete()
        await MessageSender.delete_message_and_ask_review(update, context)
        return CommonState.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    locale: Locale = context.user_data.locale
    await update.message.reply_text(context.bot_data.phrases["ask_last_name"][locale])
    return CommonState.ASK_SOURCE


async def store_last_name_ask_source(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int | None:
    """Stores the last name and asks the user how they found out about Samantha's Group."""

    if update.message is None:
        return None

    context.user_data.last_name = update.message.text

    # TODO factor out
    if (
        context.bot_data.conversation_mode_for_chat_id[context.user_data.chat_id]
        == ConversationMode.REGISTRATION_REVIEW
    ):
        await update.message.delete()
        await MessageSender.delete_message_and_ask_review(update, context)
        return CommonState.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    locale: Locale = context.user_data.locale
    await update.effective_chat.send_message(context.bot_data.phrases["ask_source"][locale])
    return CommonState.CHECK_USERNAME


async def store_source_check_username(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int | None:
    """Stores the source of knowledge about SSG, checks Telegram nickname or asks for
    phone number.
    """

    if update.message is None:
        return None

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
        await logs(
            bot=context.bot,
            text=f"{username=} will be stored in the database.",
            update=update,
        )
        locale: Locale = context.user_data.locale
        await query.edit_message_text(
            context.bot_data.phrases["ask_email"][locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return CommonState.ASK_AGE_OR_BYE_IF_PERSON_EXISTS

    context.user_data.tg_username = None
    await query.delete_message()

    await MessageSender.ask_phone_number(update, context)
    return CommonState.ASK_EMAIL


async def store_phone_ask_email(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int | None:
    """Stores the phone number and asks for email."""

    if update.message is None:
        return None

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
        await logs(
            bot=context.bot,
            level=LoggingLevel.WARNING,
            update=update,
            text=f"Could not parse phone number {phone_number_to_parse}",
        )
        parsed_phone_number = None

    # 3. Check validity and return user to same state if phone number not valid
    if parsed_phone_number and phonenumbers.is_valid_number(parsed_phone_number):
        context.user_data.phone_number = phonenumbers.format_number(
            parsed_phone_number, phonenumbers.PhoneNumberFormat.E164
        )
    else:
        await logs(
            bot=context.bot,
            level=LoggingLevel.WARNING,
            update=update,
            text=(
                f"Invalid phone number {parsed_phone_number} "
                f"(parsed from {phone_number_to_parse})"
            ),
        )
        await update.message.reply_text(
            f"{phone_number_to_parse} {context.bot_data.phrases['invalid_phone_number'][locale]}",
        )
        return CommonState.ASK_EMAIL

    if (
        context.bot_data.conversation_mode_for_chat_id[context.user_data.chat_id]
        == ConversationMode.REGISTRATION_REVIEW
    ):
        await update.message.delete()
        await MessageSender.delete_message_and_ask_review(update, context)
        return CommonState.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    await update.message.reply_text(context.bot_data.phrases["ask_email"][locale])
    await logs(
        bot=context.bot,
        update=update,
        text=f"Phone number: {context.user_data.phone_number}",
    )
    return CommonState.ASK_AGE_OR_BYE_IF_PERSON_EXISTS


async def store_email_check_existence_ask_age(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int | None:
    """Stores the email, checks existence and asks whether user wants to be student or teacher.

    Stores the email. If the user with these contact details exists, redirects to goodbye.
    Otherwise, asks age depending on role ("Are you 18+" for teacher, age group for student).
    """

    if update.message is None:
        return None

    bot_data = context.bot_data
    phrases = bot_data.phrases

    user_data = context.user_data
    locale: Locale = user_data.locale

    email = update.message.text.strip()
    if not EMAIL_PATTERN.match(email):
        await update.message.reply_text(phrases["invalid_email"][locale])
        return None

    if any(email.endswith(domain) for domain in RUSSIAN_DOMAINS):
        await update.message.reply_text(phrases["russian_email"][locale])
        return None

    user_data.email = email

    # terminate conversation if the person with these personal data already exists
    try:
        person_exists = (
            await BackendClient.person_with_first_name_last_name_email_exists_in_database(
                update, context
            )
        )
    except BackendClientError as err:
        if PERSON_EXISTENCE_CHECK_INVALID_EMAIL_MESSAGE_FROM_BACKEND in str(err):
            # Backend's rules for email validity can be different, and regex check (done above)
            # may not guarantee that the backend will accept the email.
            await logs(bot=context.bot, update=update, text=f"Backend is not happy with {email=}")
            await update.message.reply_text(phrases["invalid_email"][locale])
            return CommonState.ASK_AGE_OR_BYE_IF_PERSON_EXISTS
        else:
            raise BackendClientError("An error occurred not related to email validation") from err

    if person_exists:
        await update.message.reply_text(phrases["user_already_exists"][locale])
        return CommonState.CHAT_WITH_OPERATOR

    if (
        bot_data.conversation_mode_for_chat_id[user_data.chat_id]
        == ConversationMode.REGISTRATION_REVIEW
    ):
        await update.message.delete()
        await MessageSender.delete_message_and_ask_review(update, context)
        return CommonState.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    await getattr(MessageSender, f"ask_age_{user_data.role}")(update, context)
    return CommonState.ASK_TIMEZONE_OR_IS_YOUNG_TEACHER_READY_TO_HOST_SPEAKING_CLUB


async def ask_timezone(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Ask timezone."""

    query, _ = await answer_callback_query_and_get_data(update)
    role = context.user_data.role

    # TODO right now it is automatic that if teacher got here, they are an adult.
    #  If we start asking young teachers about timezone, we'll need to read query data here
    #  rather than using `pattern` in ConversationHandler
    if role == Role.TEACHER:
        context.user_data.teacher_is_under_18 = False

    await CQReplySender.ask_timezone(context, query)
    return (
        CommonState.TIME_SLOTS_START
        if role != Role.COORDINATOR
        else CoordinatorState.ASK_ADDITIONAL_HELP
    )


async def ask_young_teacher_if_can_host_speaking_club_or_bye_to_young_coordinator(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If this is a teacher under 18, ask if they are 16+ and can host speaking clubs. If this is
    a coordinator, say bye.

    **No students must be handled by this callback.**
    """
    query, _ = await answer_callback_query_and_get_data(update)
    user_data = context.user_data
    locale: Locale = user_data.locale
    role = user_data.role

    if role == Role.TEACHER:
        user_data.teacher_is_under_18 = True
        await CQReplySender.ask_young_teacher_is_over_16_and_ready_to_host_speaking_clubs(
            context, query
        )
        return ConversationStateTeacherUnder18.ASK_COMMUNICATION_LANGUAGE_OR_BYE
    elif role == Role.COORDINATOR:
        await update.callback_query.edit_message_text(
            context.bot_data.phrases["reply_cannot_work"][locale]
        )
        return ConversationHandler.END
    else:
        raise NotImplementedError(f"Role {role} not supported.")


async def bye_cannot_work(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Says bye to young coordinator or to young teacher that won't host speaking clubs."""
    await update.callback_query.answer()
    locale: Locale = context.user_data.locale

    await update.effective_chat.send_message(context.bot_data.phrases["reply_cannot_work"][locale])
    return ConversationHandler.END


# callbacks for asking timezone are in modules for respective roles


async def store_timezone_ask_slots_for_monday(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores timezone, asks time slots for Monday."""

    query, data = await answer_callback_query_and_get_data(update)
    user_data = context.user_data

    user_data.utc_offset_hour, user_data.utc_offset_minute = (
        int(item) for item in data.split(":")
    )

    if (
        context.bot_data.conversation_mode_for_chat_id[context.user_data.chat_id]
        == ConversationMode.REGISTRATION_REVIEW
    ):
        await MessageSender.delete_message_and_ask_review(update, context)
        return CommonState.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    await CQReplySender.ask_time_slot(context, query)
    return CommonState.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE


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

    bot_data = context.bot_data
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
    await logs(
        bot=context.bot,
        update=update,
        text=f"Slots: {', '.join(str(slot) for slot in slots_for_logging)}",
    )

    # reset day of week to Monday for possible review or re-run
    chat_data.day_index = 0

    if not any(user_data.day_and_time_slot_ids):
        locale: Locale = user_data.locale
        await query.answer(
            context.bot_data.phrases["no_slots_selected"][locale],
            show_alert=True,
        )
        await logs(
            bot=context.bot,
            update=update,
            text="User has selected no slots at all",
        )
        await CQReplySender.ask_time_slot(context, query)
        return CommonState.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE

    if (
        bot_data.conversation_mode_for_chat_id[context.user_data.chat_id]
        == ConversationMode.REGISTRATION_REVIEW
    ):
        await query.answer()
        await MessageSender.delete_message_and_ask_review(update, context)
        return CommonState.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    # If we've reached this part of function, it means that we have reached Sunday,
    # user has selected some slots, and we're not in review mode.
    # Time to ask about teaching language.

    await query.answer()
    await CQReplySender.ask_teaching_languages(context, query, show_done_button=False)

    # This is the bifurcation point in the conversation: next state depends on role.
    if user_data.role == Role.TEACHER:
        return AdultTeacherState.ASK_LEVEL_OR_ANOTHER_LANGUAGE_OR_COMMUNICATION_LANGUAGE
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

    await MessageSender.ask_yes_no(
        update, context, question_phrase_internal_id="ask_final_comment"
    )
    return CommonState.ASK_FINAL_COMMENT_TEXT_OR_BYE


async def show_review_menu(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Shows review menu to the user."""
    query, _ = await answer_callback_query_and_get_data(update)

    # Switch into review mode to let other callbacks know that they should return user
    # back to the review callback instead of moving him normally along the conversation line
    context.bot_data.conversation_mode_for_chat_id[
        context.user_data.chat_id
    ] = ConversationMode.REGISTRATION_REVIEW
    await CQReplySender.ask_review_category(context, query)
    return CommonState.REVIEW_REQUESTED_ITEM


async def ask_text_of_final_comment(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int | None:
    """Ask for final comment."""
    query, _ = await answer_callback_query_and_get_data(update)
    locale: Locale = context.user_data.locale
    await query.edit_message_text(context.bot_data.phrases["ask_final_comment_text"][locale])

    return CommonState.FINISH_REGISTRATION


async def store_comment_create_person_start_helpdesk_chat(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Store comment (if given), create a person in the backend, start conversation in helpdesk.

    For a would-be teacher that is under 18, store their comment about potential useful skills.
    For others, store the general comment."""
    user_data = context.user_data
    locale: Locale = user_data.locale
    phrases = context.bot_data.phrases
    role = user_data.role

    wait_phrase = phrases["processing_wait"][locale]
    if update.message:
        user_data.comment = update.message.text
        # saving returned Message to edit its text later on
        wait_message = await update.message.reply_text(wait_phrase)
    else:
        # user got here by pressing a button and hence didn't leave any text comment
        query, _ = await answer_callback_query_and_get_data(update)
        user_data.comment = ""
        wait_message = await query.edit_message_text(
            wait_phrase, reply_markup=InlineKeyboardMarkup([])
        )

    # Initiate conversation in helpdesk
    message_text = f"New {user_data.role}: {user_data.first_name} {user_data.last_name}"
    if context.user_data.helpdesk_conversation_id is None:
        await ChatwootClient.start_new_conversation(update, context, text=message_text)
    else:
        await ChatwootClient.send_message_to_conversation(update, context, text=message_text)

    match role:
        case Role.STUDENT:
            if user_data.student_needs_oral_interview:
                await _set_student_language_and_level_for_english_starters(update, context)
            elif user_data.student_agreed_to_smalltalk:
                await _process_student_language_and_level_from_smalltalk(update, context)

                # We just got the level from SmallTalk so if the student is too advanced
                # we have to ask them here if they want to join Speaking Club instead of group
                if (
                    user_data.student_smalltalk_result.level
                    and user_data.student_smalltalk_result.level in LEVELS_TOO_HIGH
                ):
                    await MessageSender.ask_student_with_high_level_if_wants_speaking_club(
                        update, context
                    )
                    return StudentState.CREATE_STUDENT_WITH_HIGH_LEVEL_OR_BYE

            person_was_created = await BackendClient.create_student(update, context)
        case Role.TEACHER:
            person_was_created = await BackendClient.create_adult_or_young_teacher(update, context)
        case _:
            raise NotImplementedError(f"Logic for { role=} not implemented.")

    # number of groups is None for young teachers and zero for adults that only want speaking club
    if role == Role.TEACHER and not user_data.teacher_number_of_groups:
        text = phrases["bye_wait_for_message_from_coordinator"][locale]
    elif role == Role.STUDENT and user_data.student_needs_oral_interview is True:
        text = phrases["bye_go_to_chat_with_coordinator"][locale]
    elif role == Role.STUDENT and user_data.student_assessment_resulting_level in LEVELS_TOO_HIGH:
        # Students with high results in SmallTalk get their own state (above).
        # Here we're handling those who got high level in "written" assessment and decided to go on
        # with registration despite the fact that they will only be able to attend Speaking Club.
        text = f"{phrases['student_level_too_high_we_will_email_you'][locale]} {user_data.email}"
    else:
        text = phrases["bye_wait_for_message_from_bot"][locale]

    if person_was_created is True:
        await wait_message.edit_text(text)
    else:
        await logs(
            bot=context.bot,
            text=f"Cannot send to backend: {user_data=}",
            level=LoggingLevel.CRITICAL,
            needs_to_notify_admin_group=True,
            update=update,
        )

    if user_data.student_assessment_resulting_level in LEVELS_TOO_HIGH:
        # Same as above: only students with high level in "written" assessment are handled here.
        # Students with high level in SmallTalk are handled in a separate callback.
        await notify_speaking_club_coordinator_about_high_level_student(update, context)

    return CommonState.CHAT_WITH_OPERATOR


# TERMINATORS, COMMANDS, HELPERS


async def say_bye(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Says goodbye to user without storing anything.

    This is for the case when user replies 'No' to something and the conversation
    should just end.
    """
    query, _ = await answer_callback_query_and_get_data(update)

    locale: Locale = context.user_data.locale
    await logs(bot=context.bot, text="Cancelling registration.", update=update)
    await query.edit_message_text(
        context.bot_data.phrases["bye"][locale],
        reply_markup=InlineKeyboardMarkup([]),
    )
    return CommonState.CHAT_WITH_OPERATOR


async def cancel(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Cancels and ends the conversation."""

    await logs(
        bot=context.bot,
        update=update,
        text="User aborted registration process.",
    )

    # the /cancel command could come even before the user chooses the locale
    if context.user_data.locale:
        locale: Locale = context.user_data.locale
    else:
        locale = typing.cast(Locale, update.effective_user.language_code)

    await update.message.reply_text(
        context.bot_data.phrases["bye_cancel"][locale], reply_markup=ReplyKeyboardRemove()
    )

    return CommonState.CHAT_WITH_OPERATOR


async def send_help(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
    """Display help message."""

    locale: Locale = context.user_data.locale or UKRAINIAN
    await update.message.reply_text(
        f"{context.bot_data.phrases['help'][locale]} @{BOT_TECH_SUPPORT_USERNAME}",
        reply_markup=ReplyKeyboardRemove(),
    )


async def _process_student_language_and_level_from_smalltalk(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> None:
    """Performs operations that are necessary to determine student's level of English.

    For all other languages, the logic is simple because there are no assessments.
    Language level is stored right after user chooses it during the conversation.
    """
    user_data = context.user_data
    user_data.student_smalltalk_result = await SmallTalkClient.get_result(update, context)

    if user_data.student_smalltalk_result and user_data.student_smalltalk_result.level:
        level = user_data.student_smalltalk_result.level
        await logs(
            bot=context.bot,
            update=update,
            text=f"Setting {level=} based on SmallTalk test",
        )
    else:
        level = user_data.student_assessment_resulting_level
        await logs(
            bot=context.bot,
            update=update,
            text=f"No SmallTalk result loaded or level is empty. Using {level=} from written test",
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
        await logs(
            bot=context.bot,
            update=update,
            text=(
                f"Setting level formally to A0 ({user_data.language_and_level_ids}) "
                "because user needs personal oral interview in English"
            ),
        )
        user_data.comment = f"{user_data.comment}\n- NEEDS ORAL INTERVIEW!"


async def message_fallback(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
    """Send error message."""
    bot_data = context.bot_data
    user_data = context.user_data
    chat_id = user_data.chat_id

    await logs(
        bot=context.bot,
        update=update,
        level=LoggingLevel.DEBUG,
        text=(
            "This is message fallback. "
            f"Chat mode: {bot_data.conversation_mode_for_chat_id[chat_id]}. "
            f"Effective message: {update.effective_message}"
        ),
    )

    if update.message is not None:
        await update.message.delete()

    locale: Locale = user_data.locale or UKRAINIAN
    message = await update.effective_chat.send_message(
        f"{bot_data.phrases['message_fallback'][locale]} @{BOT_TECH_SUPPORT_USERNAME}",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(5)
    await message.delete()
