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

import samanthas_telegram_bot.conversation.callbacks.registration.common as common
import samanthas_telegram_bot.conversation.callbacks.registration.student as student
import samanthas_telegram_bot.conversation.callbacks.registration.teacher as teacher
from samanthas_telegram_bot.conversation.auxil.send_to_admin_group import send_to_admin_group
from samanthas_telegram_bot.data_structures.context_types import BotData, ChatData, UserData
from samanthas_telegram_bot.data_structures.enums import ConversationState as State

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

    await send_to_admin_group(
        bot=application.bot,
        text="Registration bot started",
        parse_mode=None,
    )


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it the bot's token.
    application = (
        Application.builder()
        .token(os.environ.get("TOKEN"))
        .context_types(ContextTypes(user_data=UserData, chat_data=ChatData, bot_data=BotData))
        .post_init(post_init)
        .build()
    )

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", common.start)],
        allow_reentry=True,
        states={
            State.IS_REGISTERED: [
                CallbackQueryHandler(common.store_locale_ask_if_already_registered)
            ],
            State.CHECK_CHAT_ID_ASK_TIMEZONE: [
                CallbackQueryHandler(
                    common.redirect_to_coordinator_if_registered_check_chat_id_ask_timezone
                )
            ],
            State.CHECK_IF_WANTS_TO_REGISTER_ANOTHER_PERSON_ASK_TIMEZONE: [
                CallbackQueryHandler(
                    common.say_bye_if_does_not_want_to_register_another_or_ask_timezone
                )
            ],
            State.ASK_FIRST_NAME: [CallbackQueryHandler(common.store_timezone_ask_first_name)],
            State.ASK_LAST_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, common.store_first_name_ask_last_name
                )
            ],
            State.ASK_SOURCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, common.store_last_name_ask_source)
            ],
            State.CHECK_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, common.store_source_check_username)
            ],
            State.ASK_PHONE_NUMBER: [
                CallbackQueryHandler(common.store_username_if_available_ask_phone_or_email)
            ],
            State.ASK_EMAIL: [
                MessageHandler(
                    (filters.CONTACT ^ filters.TEXT) & ~filters.COMMAND,
                    common.store_phone_ask_email,
                )
            ],
            State.ASK_ROLE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, common.store_email_check_existence_ask_role
                )
            ],
            State.ASK_AGE: [CallbackQueryHandler(common.store_role_ask_age)],
            State.ASK_YOUNG_TEACHER_COMMUNICATION_LANGUAGE: [
                CallbackQueryHandler(
                    teacher.young_teacher_store_readiness_to_host_speaking_clubs_ask_communication_language_or_bye  # noqa
                )
            ],
            State.ASK_YOUNG_TEACHER_SPEAKING_CLUB_LANGUAGE: [
                CallbackQueryHandler(
                    teacher.young_teacher_store_communication_language_ask_speaking_club_language
                )
            ],
            State.ASK_YOUNG_TEACHER_ADDITIONAL_HELP: [
                CallbackQueryHandler(
                    teacher.young_teacher_store_teaching_language_ask_additional_help
                )
            ],
            State.TIME_SLOTS_START: [
                CallbackQueryHandler(common.store_age_ask_slots_for_one_day_or_teaching_language)
            ],
            State.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE: [
                CallbackQueryHandler(
                    common.store_age_ask_slots_for_one_day_or_teaching_language,
                    pattern="^next$",
                ),
                CallbackQueryHandler(common.store_one_time_slot_ask_another),
            ],
            State.ASK_LEVEL_OR_ANOTHER_TEACHING_LANGUAGE_OR_COMMUNICATION_LANGUAGE: [
                CallbackQueryHandler(
                    common.store_teaching_language_ask_another_or_level_or_communication_language
                ),
            ],
            State.ASK_LEVEL_OR_COMMUNICATION_LANGUAGE: [
                CallbackQueryHandler(
                    common.store_data_ask_another_level_or_communication_language_or_start_assessment
                )
            ],
            State.ASK_TEACHING_EXPERIENCE: [
                CallbackQueryHandler(teacher.store_communication_language_ask_teaching_experience)
            ],
            State.ASK_TEACHING_GROUP_OR_SPEAKING_CLUB: [
                CallbackQueryHandler(teacher.store_experience_ask_about_groups_or_speaking_clubs)
            ],
            State.ADOLESCENTS_ASK_COMMUNICATION_LANGUAGE_OR_START_ASSESSMENT: [
                CallbackQueryHandler(
                    student.ask_communication_language_or_start_assessment_depending_on_learning_experience
                )
            ],
            State.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW: [
                CallbackQueryHandler(
                    student.store_communication_language_ask_non_teaching_help_or_start_review
                )
            ],
            State.ASK_ASSESSMENT_QUESTION: [
                CallbackQueryHandler(student.assessment_store_answer_ask_question)
            ],
            State.SEND_SMALLTALK_URL_OR_ASK_COMMUNICATION_LANGUAGE: [
                CallbackQueryHandler(student.send_smalltalk_url_or_ask_communication_language)
            ],
            State.ASK_COMMUNICATION_LANGUAGE_AFTER_SMALLTALK: [
                CallbackQueryHandler(student.ask_communication_language_after_smalltalk)
            ],
            State.ASK_NUMBER_OF_GROUPS_OR_TEACHING_FREQUENCY_OR_NON_TEACHING_HELP: [
                CallbackQueryHandler(
                    teacher.store_teaching_preference_ask_groups_or_frequency_or_student_age
                )
            ],
            State.ASK_TEACHING_FREQUENCY: [
                CallbackQueryHandler(teacher.store_number_of_groups_ask_frequency)
            ],
            State.PREFERRED_STUDENT_AGE_GROUPS_START: [
                CallbackQueryHandler(teacher.store_frequency_ask_student_age_groups)
            ],
            State.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP: [
                CallbackQueryHandler(
                    teacher.store_student_age_group_ask_another_or_non_teaching_help
                )
            ],
            State.NON_TEACHING_HELP_MENU_OR_PEER_HELP_FOR_TEACHER_OR_REVIEW_FOR_STUDENT: [
                CallbackQueryHandler(common.store_non_teaching_help_ask_another_or_additional_help)
            ],
            State.PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP: [
                CallbackQueryHandler(teacher.store_peer_help_ask_another_or_additional_help)
            ],
            State.ASK_REVIEW: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    teacher.store_teachers_additional_skills_ask_if_review_needed,
                )
            ],
            State.REVIEW_MENU_OR_ASK_FINAL_COMMENT: [
                CallbackQueryHandler(
                    common.check_if_review_needed_give_review_menu_or_ask_final_comment
                )
            ],
            State.ASK_FINAL_COMMENT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    common.store_additional_help_comment_ask_final_comment,
                )
            ],
            State.REVIEW_REQUESTED_ITEM: [CallbackQueryHandler(common.review_requested_item)],
            State.BYE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, common.store_comment_end_conversation
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", common.cancel),
            MessageHandler(filters.TEXT & ~filters.COMMAND, common.message_fallback),
        ],
    )

    application.add_handler(conv_handler)

    help_handler = CommandHandler("help", common.send_help)
    application.add_handler(help_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
