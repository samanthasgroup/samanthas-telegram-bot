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
from samanthas_telegram_bot.api_queries.auxil.enums import LoggingLevel
from samanthas_telegram_bot.auxil.log_and_notify import log_and_notify
from samanthas_telegram_bot.conversation.auxil.enums import (
    CommonCallbackData,
    ConversationStateCommon,
    ConversationStateStudent,
    ConversationStateTeacher,
    UserDataReviewCategory,
)
from samanthas_telegram_bot.data_structures.constants import (
    ALL_LEVELS_PATTERN,
    ENGLISH,
    LEARNED_FOR_YEAR_OR_MORE,
)
from samanthas_telegram_bot.data_structures.context_types import (
    CUSTOM_CONTEXT_TYPES,
    BotData,
    ChatData,
    UserData,
)

load_dotenv()

logging_level = typing.cast(str, os.environ.get("LOGGING_LEVEL"))
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, logging_level),
)
logger = logging.getLogger(__name__)
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
        chat_id=os.environ.get("ADMIN_CHAT_ID"),
        text="Registration bot started",
        parse_mode=None,
    )


async def error_handler(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
    """Logs the error and send a telegram message to notify the developer."""

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    await log_and_notify(
        bot=context.bot,
        logger=logger,
        level=LoggingLevel.EXCEPTION,
        text=(
            f"@{os.environ.get('BOT_OWNER_USERNAME')} Registration bot encountered an exception:"
            f"\n<code>\n{tb_string}</code>\n"
        ),
        parse_mode_for_admin_group_message=ParseMode.HTML,
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
            ConversationStateCommon.CHECK_CHAT_ID_ASK_TIMEZONE: [
                CallbackQueryHandler(
                    common_main.redirect_to_coordinator_if_registered_check_chat_id_ask_timezone
                )
            ],
            ConversationStateCommon.CHECK_IF_WANTS_TO_REGISTER_ANOTHER_PERSON_ASK_TIMEZONE: [
                CallbackQueryHandler(
                    common_main.say_bye_if_does_not_want_to_register_another_or_ask_timezone
                )
            ],
            ConversationStateCommon.ASK_FIRST_NAME: [
                CallbackQueryHandler(common_main.store_timezone_ask_first_name)
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
            ConversationStateCommon.ASK_ROLE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    common_main.store_email_check_existence_ask_role,
                )
            ],
            ConversationStateCommon.ASK_AGE: [
                CallbackQueryHandler(common_main.store_role_ask_age)
            ],
            # Callbacks for asking day and time slots differ slightly, depending on role
            ConversationStateStudent.TIME_SLOTS_START: [
                CallbackQueryHandler(student.store_age_ask_slots_for_monday)
            ],
            ConversationStateTeacher.TIME_SLOTS_START_OR_ASK_YOUNG_TEACHER_ABOUT_SPEAKING_CLUB: [
                CallbackQueryHandler(
                    adult_teacher.ask_adult_teacher_slots_for_monday,
                    pattern=CommonCallbackData.YES,  # "Yes, I am 18 or older"
                ),
                CallbackQueryHandler(
                    adult_teacher.ask_young_teacher_readiness_to_host_speaking_club
                ),
            ],
            # Menu of time slots works the same for students and teachers
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
            ConversationStateStudent.ASK_QUESTION_IN_TEST: [
                CallbackQueryHandler(student.assessment_store_answer_ask_question)
            ],
            ConversationStateStudent.SEND_SMALLTALK_URL_OR_ASK_COMMUNICATION_LANGUAGE: [
                CallbackQueryHandler(student.send_smalltalk_url_or_ask_communication_language)
            ],
            ConversationStateStudent.ASK_COMMUNICATION_LANGUAGE_AFTER_SMALLTALK: [
                CallbackQueryHandler(student.ask_communication_language_after_smalltalk)
            ],
            ConversationStateStudent.NON_TEACHING_HELP_MENU_OR_ASK_REVIEW: [
                CallbackQueryHandler(student.ask_review, pattern=CommonCallbackData.DONE),
                CallbackQueryHandler(student.store_non_teaching_help_ask_another),
            ],
            # MIDDLE OF CONVERSATION: ADULT TEACHER CALLBACKS
            ConversationStateTeacher.ASK_LEVEL_OR_ANOTHER_LANGUAGE_OR_COMMUNICATION_LANGUAGE: [
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
            ConversationStateTeacher.ASK_TEACHING_EXPERIENCE: [
                CallbackQueryHandler(
                    adult_teacher.store_communication_language_ask_teaching_experience
                )
            ],
            ConversationStateTeacher.ASK_TEACHING_GROUP_OR_SPEAKING_CLUB: [
                CallbackQueryHandler(
                    adult_teacher.store_experience_ask_teaching_groups_vs_hosting_speaking_clubs
                )
            ],
            ConversationStateTeacher.ASK_NUMBER_OF_GROUPS_OR_FREQUENCY_OR_NON_TEACHING_HELP: [
                CallbackQueryHandler(
                    adult_teacher.store_teaching_preference_ask_groups_or_frequency_or_student_age
                )
            ],
            ConversationStateTeacher.ASK_TEACHING_FREQUENCY: [
                CallbackQueryHandler(adult_teacher.store_number_of_groups_ask_frequency)
            ],
            ConversationStateTeacher.PREFERRED_STUDENT_AGE_GROUPS_START: [
                CallbackQueryHandler(adult_teacher.store_frequency_ask_student_age_groups)
            ],
            ConversationStateTeacher.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP: [
                CallbackQueryHandler(
                    adult_teacher.ask_non_teaching_help, pattern=CommonCallbackData.DONE
                ),
                CallbackQueryHandler(adult_teacher.store_student_age_group_ask_another),
            ],
            ConversationStateTeacher.NON_TEACHING_HELP_MENU_OR_ASK_PEER_HELP_OR_ADDITIONAL_HELP: [
                CallbackQueryHandler(
                    adult_teacher.ask_peer_help_or_additional_help, pattern=CommonCallbackData.DONE
                ),
                CallbackQueryHandler(adult_teacher.store_non_teaching_help_ask_another),
            ],
            ConversationStateTeacher.PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP: [
                CallbackQueryHandler(
                    adult_teacher.ask_additional_help, pattern=CommonCallbackData.DONE
                ),
                CallbackQueryHandler(adult_teacher.store_peer_help_ask_another),
            ],
            # MIDDLE OF CONVERSATION: YOUNG TEACHER CALLBACKS
            ConversationStateTeacher.YOUNG_TEACHER_ASK_COMMUNICATION_LANGUAGE_OR_BYE: [
                CallbackQueryHandler(
                    young_teacher.ask_communication_language,
                    pattern=CommonCallbackData.YES,  # "Yes, I'm ready to host speaking clubs"
                ),
                CallbackQueryHandler(young_teacher.bye, pattern=CommonCallbackData.NO),
            ],
            ConversationStateTeacher.ASK_YOUNG_TEACHER_SPEAKING_CLUB_LANGUAGE: [
                CallbackQueryHandler(
                    young_teacher.store_communication_language_ask_speaking_club_language
                )
            ],
            ConversationStateTeacher.ASK_YOUNG_TEACHER_ADDITIONAL_HELP: [
                CallbackQueryHandler(
                    young_teacher.store_speaking_club_language_ask_additional_help
                )
            ],
            ConversationStateTeacher.ASK_REVIEW: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    adult_teacher.store_additional_help_ask_review,
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
            ConversationStateCommon.ASK_FINAL_COMMENT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    common_main.store_additional_help_comment_ask_final_comment,
                )
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
