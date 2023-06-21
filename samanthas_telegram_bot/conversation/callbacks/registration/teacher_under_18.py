import logging

from telegram import Update
from telegram.ext import ConversationHandler

from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.conversation.auxil.enums import (
    ConversationStateCommon,
    ConversationStateTeacherUnder18,
)
from samanthas_telegram_bot.conversation.auxil.shortcuts import answer_callback_query_and_get_data
from samanthas_telegram_bot.data_structures.constants import Locale
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES

logger = logging.getLogger(__name__)


async def ask_readiness_to_host_speaking_club(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Asks if the young teacher is 16+ and can host speaking clubs."""
    query, _ = await answer_callback_query_and_get_data(update)
    context.user_data.teacher_is_under_18 = True

    await CQReplySender.ask_young_teacher_is_over_16_and_ready_to_host_speaking_clubs(
        context, query
    )
    return ConversationStateTeacherUnder18.ASK_COMMUNICATION_LANGUAGE_OR_BYE


async def bye_cannot_work(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Says bye to a young teacher that doesn't want to host speaking clubs."""
    await update.callback_query.answer()

    await update.effective_chat.send_message(
        context.bot_data.phrases["reply_cannot_work"][context.user_data.locale]
    )
    return ConversationHandler.END


async def ask_communication_language(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Young teacher is ready to host speaking clubs: asks for communication language."""
    query, _ = await answer_callback_query_and_get_data(update)
    context.user_data.teacher_can_host_speaking_club = True

    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationStateTeacherUnder18.ASK_SPEAKING_CLUB_LANGUAGE


async def store_communication_language_ask_speaking_club_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores communication language, asks language of speaking clubs they want to host."""
    (
        query,
        context.user_data.communication_language_in_class,
    ) = await answer_callback_query_and_get_data(update)

    await CQReplySender.ask_teaching_languages(context, query, show_done_button=False)
    return ConversationStateTeacherUnder18.ASK_ADDITIONAL_SKILLS_COMMENT


async def store_speaking_club_language_ask_additional_skills_comment(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores teaching language, asks additional skills."""
    query, lang_id = await answer_callback_query_and_get_data(update)
    await query.delete_message()

    logger.info(
        f"Chat {update.effective_chat.id}. Young teacher wants to host speaking clubs in {lang_id}"
    )

    # TODO this is a temporary measure to keep things simple as there are very few young teachers.
    #  For now we just say that a young teacher who wants to host speaking club only chooses
    #  one single language and we automatically add pre-intermediate level to it (one cannot choose
    #  level higher than A2 for any language other than English).
    #  Maybe we will need to add some more logic, but maybe not.  Speaking clubs are informal.
    context.user_data.language_and_level_ids = [
        context.bot_data.language_and_level_id_for_language_id_and_level[(lang_id, "A2")]
    ]

    await update.effective_chat.send_message(
        context.bot_data.phrases["ask_teacher_any_additional_help"][context.user_data.locale]
    )
    return ConversationStateTeacherUnder18.ASK_FINAL_COMMENT


class CommonState:
    pass


async def store_additional_help_comment_ask_final_comment(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """For young teachers: stores comment on additional help, asks for final comment."""
    if update.message is None:
        return ConversationStateTeacherUnder18.ASK_FINAL_COMMENT
    locale: Locale = context.user_data.locale

    context.user_data.teacher_additional_skills_comment = update.message.text

    # We want to give the young teacher the opportunity to double-check their email
    # without starting a full-fledged review
    await update.message.reply_text(
        f"{context.bot_data.phrases['young_teacher_we_will_email_you'][locale]} "
        f"{context.user_data.email}\n\n"
        f"{context.bot_data.phrases['ask_final_comment'][locale]}"
    )
    return ConversationStateCommon.BYE
