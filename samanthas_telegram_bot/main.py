import logging
import os
import traceback
import typing

from dotenv import load_dotenv
from telegram import BotCommandScopeAllPrivateChats, Update
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

import samanthas_telegram_bot.conversation.callbacks.registration.common_main_flow as common_main
import samanthas_telegram_bot.conversation.callbacks.registration.common_review as review
import samanthas_telegram_bot.conversation.callbacks.registration.student as student
import samanthas_telegram_bot.conversation.callbacks.registration.teacher_adult as adult_teacher
import samanthas_telegram_bot.conversation.callbacks.registration.teacher_under_18 as young_teacher
from samanthas_telegram_bot.auxil.constants import ADMIN_CHAT_ID, BOT_OWNER_USERNAME, LOGGING_LEVEL
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.conversation.auxil.enums import (
    CommonCallbackData,
    ConversationStateCommon,
    ConversationStateStudent,
    ConversationStateTeacherAdult,
    ConversationStateTeacherUnder18,
    UserDataReviewCategory,
)
from samanthas_telegram_bot.data_structures.constants import (
    ALL_LEVELS_PATTERN,
    ENGLISH,
    EXCEPTION_TRACEBACK_CLEANUP_PATTERN,
    LEARNED_FOR_YEAR_OR_MORE,
)
from samanthas_telegram_bot.data_structures.context_types import (
    CUSTOM_CONTEXT_TYPES,
    BotData,
    ChatData,
    UserData,
)
from samanthas_telegram_bot.data_structures.enums import LoggingLevel

load_dotenv()

logging_level = typing.cast(str, LOGGING_LEVEL)
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s | %(module)s (%(funcName)s:%(lineno)s)",
    level=getattr(logging, logging_level),
)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def post_init(application: Application) -> None:
    await application.bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())
    await application.bot.set_my_commands(
        [
            ("start", "Start registration"),
            ("cancel", "Cancel registration"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
        language_code="en",
    )
    await application.bot.set_my_commands(
        [
            ("start", "Начать регистрацию"),
            ("cancel", "Отменить регистрацию"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
        language_code="ru",
    )
    await application.bot.set_my_commands(
        [
            ("start", "Почати реєстрацію"),
            ("cancel", "Перервати реєстрацію"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
        language_code="ua",
    )

    await application.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text="Registration bot started",
        parse_mode=None,
    )


async def error_handler(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
    """Logs the error and send a telegram message to notify the developer."""

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)

    tb_string = "".join(
        EXCEPTION_TRACEBACK_CLEANUP_PATTERN.sub("", item)
        for item in tb_list
        if "/virtualenvs/" not in item  # don't show traceback lines from external modules
    )
    tb_string = f"<code>{tb_string}</code>"

    if update.message is not None:
        tb_string = (
            f"{tb_string}\n<strong>Message received from user</strong>: {update.message.text}\n"
        )
        # TODO this will not work for now because the user has to reply to the message,
        #  not just send his message after bot's.  This could be solved by ForceReply()
        #  as reply_markup where possible.
        if update.message.reply_to_message is not None:
            tb_string = (
                f"{tb_string}\n<strong>This was a reply to message from bot</strong>: "
                f"{update.message.reply_to_message.text}\n"
            )

    if update.callback_query is not None:
        tb_string = (
            f"{tb_string}\n<strong>Message the user reacted to</strong> (first 100 chars):\n\n"
            f"{update.effective_message.text[:100]}...\n\n"
            f"<strong>Data from button pressed</strong>: {update.callback_query.data}\n"
        )

    await logs(
        bot=context.bot,
        update=update,
        level=LoggingLevel.EXCEPTION,
        text=(
            "Registration bot encountered an exception:"
            f"\n\n{tb_string}\n"
            f"@{BOT_OWNER_USERNAME}"
        ),
        parse_mode_for_admin_group_message=ParseMode.HTML,
        needs_to_notify_admin_group=True,
    )


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it the bot's token.
    application = (
        Application.builder()
        .token(os.environ.get("BOT_TOKEN"))
        .context_types(ContextTypes(user_data=UserData, chat_data=ChatData, bot_data=BotData))
        .post_init(post_init)
        .build()
    )

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", common_main.start),
        ],
        allow_reentry=True,
        states={
            # COMMON START OF CONVERSATION
            ConversationStateCommon.IS_REGISTERED: [
                CallbackQueryHandler(common_main.store_locale_ask_if_already_registered)
            ],
            ConversationStateCommon.CHECK_CHAT_ID_ASK_ROLE: [
                CallbackQueryHandler(
                    common_main.redirect_registered_user_to_coordinator,
                    pattern=CommonCallbackData.YES,  # "Yes, I am already registered here"
                ),
                CallbackQueryHandler(common_main.check_chat_id_ask_role_if_id_does_not_exist),
            ],
            ConversationStateCommon.ASK_ROLE_OR_BYE: [
                CallbackQueryHandler(
                    common_main.say_bye_if_does_not_want_to_register_another_person,
                    pattern=CommonCallbackData.NO,  # "No, I don't want to register anyone else"
                ),
                CallbackQueryHandler(common_main.ask_role),
            ],
            ConversationStateCommon.SHOW_DISCLAIMER: [
                CallbackQueryHandler(common_main.store_role_show_disclaimer)
            ],
            ConversationStateCommon.ASK_FIRST_NAME_OR_BYE: [
                CallbackQueryHandler(
                    common_main.say_bye_if_disclaimer_not_accepted,
                    pattern=CommonCallbackData.ABORT,
                ),
                CallbackQueryHandler(common_main.ask_first_name),
            ],
            ConversationStateCommon.ASK_LAST_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, common_main.store_first_name_ask_last_name
                )
            ],
            ConversationStateCommon.ASK_SOURCE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, common_main.store_last_name_ask_source
                )
            ],
            ConversationStateCommon.CHECK_USERNAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, common_main.store_source_check_username
                )
            ],
            ConversationStateCommon.ASK_PHONE_NUMBER: [
                CallbackQueryHandler(common_main.store_username_if_available_ask_phone_or_email)
            ],
            ConversationStateCommon.ASK_EMAIL: [
                MessageHandler(
                    (filters.CONTACT ^ filters.TEXT) & ~filters.COMMAND,
                    common_main.store_phone_ask_email,
                )
            ],
            ConversationStateCommon.ASK_AGE_OR_BYE_IF_PERSON_EXISTS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    common_main.store_email_check_existence_ask_age,
                )
            ],
            # Callbacks for asking timezone depend on role (don't ask teen teachers about timezone)
            ConversationStateCommon.ASK_TIMEZONE_OR_IS_YOUNG_TEACHER_READY_TO_HOST_SPEAKING_CLUB: [
                CallbackQueryHandler(
                    adult_teacher.ask_timezone,
                    pattern=CommonCallbackData.YES,  # Teacher: "Yes, I am 18 or older"
                ),
                CallbackQueryHandler(
                    young_teacher.ask_readiness_to_host_speaking_club,
                    pattern=CommonCallbackData.NO,
                ),
                # students don't reply "yes" or "no": they choose their age group
                CallbackQueryHandler(student.store_age_ask_timezone),
            ],
            # Callbacks for asking day and time slots (2 states: start and menu) are the same
            ConversationStateCommon.TIME_SLOTS_START: [
                CallbackQueryHandler(common_main.store_timezone_ask_slots_for_monday)
            ],
            ConversationStateCommon.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE: [
                CallbackQueryHandler(
                    common_main.store_last_time_slot_ask_slots_for_next_day_or_teaching_language,
                    pattern=CommonCallbackData.NEXT,
                ),
                CallbackQueryHandler(common_main.store_one_time_slot_ask_another),
            ],
            # MIDDLE OF CONVERSATION: STUDENT CALLBACKS
            ConversationStateStudent.ASK_LEVEL_OR_COMMUNICATION_LANGUAGE_OR_START_TEST: [
                CallbackQueryHandler(
                    student.ask_if_can_read_in_english,
                    pattern=ENGLISH,
                ),
                CallbackQueryHandler(
                    student.store_teaching_language_ask_level,
                    pattern=r"^[a-z]{2}$",  # two-letter code of language (if 'en' didn't match)
                ),
                CallbackQueryHandler(
                    student.store_non_english_level_ask_communication_language,
                    pattern=ALL_LEVELS_PATTERN,
                ),
            ],
            ConversationStateStudent.ENGLISH_STUDENTS_ASK_COMMUNICATION_LANGUAGE_OR_START_TEST_DEPENDING_ON_ABILITY_TO_READ: [  # noqa:E501
                CallbackQueryHandler(
                    student.ask_or_start_assessment_for_english_reader_depending_on_age,
                    pattern=CommonCallbackData.YES,  # "yes, I can read in English"
                ),
                CallbackQueryHandler(
                    student.ask_communication_language_for_students_that_cannot_read_in_english,
                    pattern=CommonCallbackData.NO,
                ),
            ],
            ConversationStateStudent.ADOLESCENTS_ASK_COMMUNICATION_LANGUAGE_OR_START_TEST: [
                CallbackQueryHandler(
                    student.start_assessment_for_teen_student_that_learned_for_year_or_more,
                    pattern=LEARNED_FOR_YEAR_OR_MORE,
                ),
                CallbackQueryHandler(
                    student.ask_communication_language_for_teen_student_that_learned_less_than_year
                ),
            ],
            ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW: [
                CallbackQueryHandler(
                    student.store_communication_language_ask_non_teaching_help_or_start_review
                )
            ],
            ConversationStateStudent.ASK_QUESTION_IN_TEST_OR_GET_RESULTING_LEVEL: [
                CallbackQueryHandler(
                    student.assessment_ask_first_question,
                    pattern=CommonCallbackData.OK,  # "OK, let's start the test"
                ),
                CallbackQueryHandler(
                    student.get_result_of_aborted_assessment,
                    pattern=CommonCallbackData.ABORT,
                ),
                CallbackQueryHandler(
                    student.store_assessment_answer_ask_next_question_or_get_result_if_finished
                ),
            ],
            ConversationStateStudent.SEND_SMALLTALK_URL_OR_ASK_COMMUNICATION_LANGUAGE: [
                CallbackQueryHandler(student.send_smalltalk_url, pattern=CommonCallbackData.YES),
                CallbackQueryHandler(student.skip_smalltalk_ask_communication_language),
            ],
            ConversationStateStudent.ASK_COMMUNICATION_LANGUAGE_AFTER_SMALLTALK: [
                CallbackQueryHandler(student.ask_communication_language_after_smalltalk)
            ],
            ConversationStateStudent.NON_TEACHING_HELP_MENU_OR_ASK_REVIEW: [
                CallbackQueryHandler(student.ask_review, pattern=CommonCallbackData.DONE),
                CallbackQueryHandler(student.store_non_teaching_help_ask_another),
            ],
            # MIDDLE OF CONVERSATION: ADULT TEACHER CALLBACKS
            ConversationStateTeacherAdult.ASK_LEVEL_OR_ANOTHER_LANGUAGE_OR_COMMUNICATION_LANGUAGE: [  # noqa:E501
                CallbackQueryHandler(
                    adult_teacher.ask_class_communication_language,
                    pattern=CommonCallbackData.DONE,
                ),
                CallbackQueryHandler(
                    adult_teacher.ask_next_teaching_language,
                    pattern=CommonCallbackData.NEXT,
                ),
                CallbackQueryHandler(
                    adult_teacher.store_level_ask_another,
                    pattern=ALL_LEVELS_PATTERN,
                ),
                CallbackQueryHandler(adult_teacher.store_teaching_language_ask_level),
            ],
            ConversationStateTeacherAdult.ASK_TEACHING_EXPERIENCE: [
                CallbackQueryHandler(
                    adult_teacher.store_communication_language_ask_teaching_experience
                )
            ],
            ConversationStateTeacherAdult.ASK_TEACHING_GROUP_OR_SPEAKING_CLUB: [
                CallbackQueryHandler(
                    adult_teacher.store_experience_ask_teaching_groups_vs_hosting_speaking_clubs
                )
            ],
            ConversationStateTeacherAdult.ASK_NUMBER_OF_GROUPS_OR_FREQUENCY_OR_NON_TEACHING_HELP: [
                CallbackQueryHandler(
                    adult_teacher.store_teaching_preference_ask_groups_or_frequency_or_student_age
                )
            ],
            ConversationStateTeacherAdult.ASK_TEACHING_FREQUENCY: [
                CallbackQueryHandler(adult_teacher.store_number_of_groups_ask_frequency)
            ],
            ConversationStateTeacherAdult.PREFERRED_STUDENT_AGE_GROUPS_START: [
                CallbackQueryHandler(adult_teacher.store_frequency_ask_student_age_groups)
            ],
            ConversationStateTeacherAdult.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP: [  # noqa:E501
                CallbackQueryHandler(
                    adult_teacher.ask_non_teaching_help, pattern=CommonCallbackData.DONE
                ),
                CallbackQueryHandler(adult_teacher.store_student_age_group_ask_another),
            ],
            ConversationStateTeacherAdult.NON_TEACHING_HELP_MENU_OR_ASK_PEER_HELP_OR_ADDITIONAL_HELP: [  # noqa:E501
                CallbackQueryHandler(
                    adult_teacher.ask_peer_help_or_additional_help, pattern=CommonCallbackData.DONE
                ),
                CallbackQueryHandler(adult_teacher.store_non_teaching_help_ask_another),
            ],
            ConversationStateTeacherAdult.PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP: [
                CallbackQueryHandler(
                    adult_teacher.ask_additional_skills_comment, pattern=CommonCallbackData.DONE
                ),
                CallbackQueryHandler(adult_teacher.store_peer_help_ask_another),
            ],
            ConversationStateTeacherAdult.ASK_REVIEW: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    adult_teacher.store_additional_skills_comment_ask_review,
                )
            ],
            # MIDDLE OF CONVERSATION: YOUNG TEACHER CALLBACKS
            ConversationStateTeacherUnder18.ASK_COMMUNICATION_LANGUAGE_OR_BYE: [
                CallbackQueryHandler(
                    young_teacher.ask_communication_language,
                    pattern=CommonCallbackData.YES,  # "Yes, I'm ready to host speaking clubs"
                ),
                CallbackQueryHandler(young_teacher.bye_cannot_work, pattern=CommonCallbackData.NO),
            ],
            ConversationStateTeacherUnder18.ASK_SPEAKING_CLUB_LANGUAGE: [
                CallbackQueryHandler(
                    young_teacher.store_communication_language_ask_speaking_club_language
                )
            ],
            ConversationStateTeacherUnder18.ASK_ADDITIONAL_SKILLS_COMMENT: [
                CallbackQueryHandler(
                    young_teacher.store_speaking_club_language_ask_additional_skills_comment
                )
            ],
            # young teachers don't get to the review
            ConversationStateTeacherUnder18.ASK_FINAL_COMMENT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    young_teacher.store_additional_help_comment_ask_final_comment,
                )
            ],
            # COMMON FINAL PART OF CONVERSATION:
            ConversationStateCommon.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU: [
                CallbackQueryHandler(
                    common_main.ask_final_comment,
                    pattern=CommonCallbackData.YES,  # "Yes, info is correct (no review needed)"
                ),
                CallbackQueryHandler(common_main.show_review_menu),
            ],
            ConversationStateCommon.REVIEW_REQUESTED_ITEM: [
                CallbackQueryHandler(review.first_name, pattern=UserDataReviewCategory.FIRST_NAME),
                CallbackQueryHandler(review.last_name, pattern=UserDataReviewCategory.LAST_NAME),
                CallbackQueryHandler(review.phone, pattern=UserDataReviewCategory.PHONE_NUMBER),
                CallbackQueryHandler(review.email, pattern=UserDataReviewCategory.EMAIL),
                CallbackQueryHandler(review.timezone, pattern=UserDataReviewCategory.TIMEZONE),
                CallbackQueryHandler(
                    review.day_and_time_slots, pattern=UserDataReviewCategory.DAY_AND_TIME_SLOTS
                ),
                CallbackQueryHandler(
                    review.languages_and_levels,
                    pattern=UserDataReviewCategory.LANGUAGES_AND_LEVELS,
                ),
                CallbackQueryHandler(
                    review.class_communication_language,
                    pattern=UserDataReviewCategory.CLASS_COMMUNICATION_LANGUAGE,
                ),
                CallbackQueryHandler(
                    review.student_age_groups, pattern=UserDataReviewCategory.STUDENT_AGE_GROUPS
                ),
            ],
            ConversationStateCommon.BYE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, common_main.store_comment_end_conversation
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", common_main.cancel),
            MessageHandler(filters.TEXT & ~filters.COMMAND, common_main.message_fallback),
        ],
    )

    application.add_handler(conv_handler)

    help_handler = CommandHandler("help", common_main.send_help)
    application.add_handler(help_handler)

    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
