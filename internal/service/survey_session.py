from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from internal.domain.models import AnswerOption, Question
from internal.repository.contracts import SurveyRepository, UserRepository


class SurveyQuestions(Protocol):
    def create(self, survey_id: UUID, text: str, type: str, position: int,
               is_required: bool = True) -> Question: ...
    def for_survey(self, survey_id: UUID) -> list[Question]: ...


class QuestionOptions(Protocol):
    def create(self, question_id: UUID, text: str, position: int) -> AnswerOption: ...
    def for_question(self, question_id: UUID) -> list[AnswerOption]: ...


@dataclass
class SurveySession:
    users: UserRepository
    surveys: SurveyRepository
    questions: SurveyQuestions
    options: QuestionOptions


SessionFactory = Callable[[], AbstractContextManager[SurveySession]]
Clock = Callable[[], datetime]
