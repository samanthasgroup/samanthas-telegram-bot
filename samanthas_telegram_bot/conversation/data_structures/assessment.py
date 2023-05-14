from typing import NamedTuple


class AssessmentQuestionOption(NamedTuple):
    id: int
    text: str


class AssessmentQuestion(NamedTuple):
    id: int
    text: str
    options: tuple[AssessmentQuestionOption, ...]


class Assessment(NamedTuple):
    id: int
    age_range_ids: tuple[int, ...]
    questions: tuple[AssessmentQuestion, ...]
