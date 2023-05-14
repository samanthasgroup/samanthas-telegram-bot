from typing import NamedTuple


class AssessmentQuestionOption(NamedTuple):
    id: str
    text: str


class AssessmentQuestion(NamedTuple):
    id: str
    text: str
    options: tuple[AssessmentQuestionOption, ...]


class Assessment(NamedTuple):
    id: str
    age_range_ids: tuple[int, ...]
    questions: tuple[AssessmentQuestion, ...]
