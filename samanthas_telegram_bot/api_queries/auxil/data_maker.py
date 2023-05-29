import json

from telegram import Update

from samanthas_telegram_bot.api_queries.auxil.constants import DataDict
from samanthas_telegram_bot.data_structures.context_types import UserData


class DataMaker:
    """Class for creating data dictionaries to be sent to backend."""

    STATUS_AT_CREATION_STUDENT_TEACHER = "awaiting_offer"
    STATUS_AT_CREATION_TEACHER_UNDER_18 = "active"

    @staticmethod
    def personal_info(user_data: UserData) -> DataDict:
        return {
            "communication_language_mode": user_data.communication_language_in_class,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "telegram_username": user_data.tg_username if user_data.tg_username else "",
            "email": user_data.email,
            "phone": user_data.phone_number,
            "utc_timedelta": f"{user_data.utc_offset_hour:02d}:{user_data.utc_offset_minute}:00",
            "information_source": user_data.source,
            "registration_telegram_bot_chat_id": user_data.chat_id,
            "registration_telegram_bot_language": user_data.locale,
        }

    @classmethod
    def student(cls, update: Update, personal_info_id: int, user_data: UserData) -> DataDict:
        data: DataDict = {
            "personal_info": personal_info_id,
            "comment": user_data.comment,
            "status": cls.STATUS_AT_CREATION_STUDENT_TEACHER,
            "status_since": cls._format_status_since(update),
            "can_read_in_english": user_data.student_can_read_in_english,
            "is_member_of_speaking_club": False,  # TODO can backend set to False by default?
            "age_range": user_data.student_age_range_id,
            "availability_slots": user_data.day_and_time_slot_ids,
            "non_teaching_help_required": user_data.non_teaching_help_types,
            "teaching_languages_and_levels": user_data.language_and_level_ids,
        }
        if user_data.student_smalltalk_result:
            data["smalltalk_test_result"] = json.dumps(
                str(user_data.student_smalltalk_result.original_json)
            )
            # TODO url (when field in backend is created)
        return data

    @staticmethod
    def student_enrollment_test(personal_info_id: int, user_data: UserData) -> DataDict:
        if user_data.student_assessment_answers is None:
            raise TypeError(
                "Don't pass user_data with no student assessment answers to this method"
            )
        return {
            "student": personal_info_id,
            "answers": [item.answer_id for item in user_data.student_assessment_answers],
        }

    @classmethod
    def teacher(cls, update: Update, personal_info_id: int, user_data: UserData) -> DataDict:
        peer_help = user_data.teacher_peer_help

        return {
            "personal_info": personal_info_id,
            "comment": user_data.comment,
            "status": cls.STATUS_AT_CREATION_STUDENT_TEACHER,
            "status_since": cls._format_status_since(update),
            "can_host_speaking_club": user_data.teacher_can_host_speaking_club,
            "has_hosted_speaking_club": False,
            "is_validated": False,
            "has_prior_teaching_experience": user_data.teacher_has_prior_experience,
            "non_teaching_help_provided_comment": user_data.teacher_additional_skills_comment,
            "peer_support_can_check_syllabus": peer_help.can_check_syllabus,
            "peer_support_can_host_mentoring_sessions": peer_help.can_host_mentoring_sessions,
            "peer_support_can_give_feedback": peer_help.can_give_feedback,
            "peer_support_can_help_with_childrens_groups": peer_help.can_help_with_children_group,
            "peer_support_can_provide_materials": peer_help.can_provide_materials,
            "peer_support_can_invite_to_class": peer_help.can_invite_to_class,
            "peer_support_can_work_in_tandem": peer_help.can_work_in_tandem,
            "simultaneous_groups": user_data.teacher_number_of_groups,
            "weekly_frequency_per_group": user_data.teacher_class_frequency,
            "availability_slots": user_data.day_and_time_slot_ids,
            "non_teaching_help_provided": user_data.non_teaching_help_types,
            "student_age_ranges": user_data.teacher_student_age_range_ids,
            "teaching_languages_and_levels": user_data.language_and_level_ids,
        }

    @classmethod
    def teacher_under_18(
        cls, update: Update, personal_info_id: int, user_data: UserData
    ) -> DataDict:
        return {
            "personal_info": personal_info_id,
            "comment": user_data.comment,
            "status_since": cls._format_status_since(update),
            "status": cls.STATUS_AT_CREATION_TEACHER_UNDER_18,
            "can_host_speaking_club": user_data.teacher_can_host_speaking_club,
            "has_hosted_speaking_club": False,
            "is_validated": False,
            "non_teaching_help_provided_comment": user_data.teacher_additional_skills_comment,
            "teaching_languages_and_levels": user_data.language_and_level_ids,
        }

    @staticmethod
    def _format_status_since(update: Update) -> str:
        """Converts a datetime object into suitable format for `status_since` field."""
        # TODO can/should backend do this?
        return update.effective_message.date.isoformat().replace("+00:00", "Z")
