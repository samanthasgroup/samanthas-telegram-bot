import logging
import os

from telegram import BotCommandScopeAllPrivateChats
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from samanthas_telegram_bot.conversation.callbacks.common import (
    cancel,
    check_if_review_needed_give_review_menu_or_ask_final_comment,
    redirect_to_coordinator_if_registered_check_chat_id_ask_first_name,
    review_requested_item,
    say_bye_if_does_not_want_to_register_another_or_ask_first_name,
    send_help,
    start,
    store_additional_help_comment_ask_final_comment,
    store_age_ask_timezone,
    store_comment_end_conversation,
    store_data_ask_another_level_or_communication_language_or_start_assessment,
    store_email_check_existence_ask_role,
    store_first_name_ask_last_name,
    store_last_name_ask_source,
    store_locale_ask_if_already_registered,
    store_non_teaching_help_ask_another_or_additional_help,
    store_one_time_slot_ask_another,
    store_phone_ask_email,
    store_role_ask_age,
    store_source_check_username,
    store_teaching_language_ask_another_or_level_or_communication_language,
    store_timezone_ask_slots_for_one_day_or_teaching_language,
    store_username_if_available_ask_phone_or_email,
)
from samanthas_telegram_bot.conversation.callbacks.student import (
    ask_communication_language_after_smalltalk,
    ask_communication_language_or_start_assessment_depending_on_learning_experience,
    assessment_store_answer_ask_question,
    send_smalltalk_url_or_ask_communication_language,
    store_communication_language_ask_non_teaching_help_or_start_review,
)
from samanthas_telegram_bot.conversation.callbacks.teacher import (
    store_communication_language_ask_teaching_experience,
    store_experience_ask_about_groups_or_speaking_clubs,
    store_frequency_ask_student_age_groups,
    store_number_of_groups_ask_frequency,
    store_peer_help_ask_another_or_additional_help,
    store_readiness_to_host_speaking_clubs_ask_additional_help_or_bye,
    store_student_age_group_ask_another_or_non_teaching_help,
    store_teachers_additional_skills_ask_if_review_needed,
    store_teaching_preference_ask_groups_or_frequency_or_student_age,
)
from samanthas_telegram_bot.conversation.constants_dataclasses.constants_enums import (
    ConversationState as State,
)
from samanthas_telegram_bot.conversation.constants_dataclasses.user_data import UserData

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
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
            State.IS_REGISTERED: [CallbackQueryHandler(store_locale_ask_if_already_registered)],
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
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, store_email_check_existence_ask_role
                )
            ],
            State.ASK_AGE: [CallbackQueryHandler(store_role_ask_age)],
            State.ASK_YOUNG_TEACHER_ADDITIONAL_HELP: [
                CallbackQueryHandler(
                    store_readiness_to_host_speaking_clubs_ask_additional_help_or_bye
                )
            ],
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
                    store_data_ask_another_level_or_communication_language_or_start_assessment
                )
            ],
            State.ASK_TEACHING_EXPERIENCE: [
                CallbackQueryHandler(store_communication_language_ask_teaching_experience)
            ],
            State.ASK_TEACHING_GROUP_OR_SPEAKING_CLUB: [
                CallbackQueryHandler(store_experience_ask_about_groups_or_speaking_clubs)
            ],
            State.ADOLESCENTS_ASK_COMMUNICATION_LANGUAGE_OR_START_ASSESSMENT: [
                CallbackQueryHandler(
                    ask_communication_language_or_start_assessment_depending_on_learning_experience
                )
            ],
            State.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW: [
                CallbackQueryHandler(
                    store_communication_language_ask_non_teaching_help_or_start_review
                )
            ],
            State.ASK_ASSESSMENT_QUESTION: [
                CallbackQueryHandler(assessment_store_answer_ask_question)
            ],
            State.SEND_SMALLTALK_URL_OR_ASK_COMMUNICATION_LANGUAGE: [
                CallbackQueryHandler(send_smalltalk_url_or_ask_communication_language)
            ],
            State.ASK_COMMUNICATION_LANGUAGE_AFTER_SMALLTALK: [
                CallbackQueryHandler(ask_communication_language_after_smalltalk)
            ],
            State.ASK_NUMBER_OF_GROUPS_OR_TEACHING_FREQUENCY_OR_NON_TEACHING_HELP: [
                CallbackQueryHandler(
                    store_teaching_preference_ask_groups_or_frequency_or_student_age
                )
            ],
            State.ASK_TEACHING_FREQUENCY: [
                CallbackQueryHandler(store_number_of_groups_ask_frequency)
            ],
            State.PREFERRED_STUDENT_AGE_GROUPS_START: [
                CallbackQueryHandler(store_frequency_ask_student_age_groups)
            ],
            State.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP: [
                CallbackQueryHandler(store_student_age_group_ask_another_or_non_teaching_help)
            ],
            State.NON_TEACHING_HELP_MENU_OR_PEER_HELP_FOR_TEACHER_OR_REVIEW_FOR_STUDENT: [
                CallbackQueryHandler(store_non_teaching_help_ask_another_or_additional_help)
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
            State.ASK_FINAL_COMMENT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    store_additional_help_comment_ask_final_comment,
                )
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
