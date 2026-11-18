from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from internal.domain.errors import ErrConflict, ErrInvalidInput
from internal.domain.models import QuestionDetail, SurveyDetail
from internal.service.survey_session import Clock, SessionFactory, SurveySession


@dataclass(frozen=True)
class OptionDraft:
    text: str
    position: int


@dataclass(frozen=True)
class QuestionDraft:
    text: str
    type: str
    position: int
    is_required: bool = True
    options: tuple[OptionDraft, ...] = ()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SurveyService:
    def __init__(self, sessions: SessionFactory, clock: Clock = utc_now) -> None:
        self._sessions = sessions
        self._clock = clock

    @staticmethod
    def _check_questions(questions: list[QuestionDraft]) -> None:
        if len(questions) > 100:
            raise ErrInvalidInput("A survey may have at most 100 questions.")
        positions = [q.position for q in questions]
        if any(p < 1 for p in positions) or len(set(positions)) != len(positions):
            raise ErrInvalidInput("Question positions must be positive and unique.")
        for question in questions:
            if not 1 <= len(question.text.strip()) <= 1000:
                raise ErrInvalidInput("Question text must contain 1 to 1000 characters.")
            if question.type not in ("text", "single_choice", "multiple_choice"):
                raise ErrInvalidInput("Unknown question type.")
            if len(question.options) > 50:
                raise ErrInvalidInput("A question may have at most 50 options.")
            option_positions = [o.position for o in question.options]
            if any(p < 1 for p in option_positions) or len(set(option_positions)) != len(option_positions):
                raise ErrInvalidInput("Option positions must be positive and unique.")
            if any(not 1 <= len(o.text.strip()) <= 500 for o in question.options):
                raise ErrInvalidInput("Option text must contain 1 to 500 characters.")
            if question.type == "text" and question.options:
                raise ErrInvalidInput("Text questions cannot contain answer options.")

    @staticmethod
    def _detail(session: SurveySession, survey) -> SurveyDetail:
        questions = [
            QuestionDetail(**q.model_dump(), options=session.options.for_question(q.id))
            for q in session.questions.for_survey(survey.id)
        ]
        return SurveyDetail(**survey.model_dump(), questions=questions)

    def create(self, creator_id: UUID, title: str, description: str | None,
               questions: list[QuestionDraft]) -> SurveyDetail:
        title = title.strip()
        if not 3 <= len(title) <= 200:
            raise ErrInvalidInput("Survey title must contain 3 to 200 characters.")
        if description is not None and len(description) > 2000:
            raise ErrInvalidInput("Description must not exceed 2000 characters.")
        self._check_questions(questions)
        with self._sessions() as session:
            session.users.get_by_id(creator_id)
            survey = session.surveys.create(creator_id, title, description)
            for draft in questions:
                question = session.questions.create(
                    survey.id, draft.text.strip(), draft.type, draft.position, draft.is_required,
                )
                for option in draft.options:
                    session.options.create(question.id, option.text.strip(), option.position)
            return self._detail(session, survey)

    def get(self, survey_id: UUID) -> SurveyDetail:
        with self._sessions() as session:
            return self._detail(session, session.surveys.get_by_id(survey_id))

    def publish(self, survey_id: UUID) -> SurveyDetail:
        with self._sessions() as session:
            survey = session.surveys.get_for_update(survey_id)
            if survey.status != "draft":
                raise ErrConflict("Only a draft survey can be published.")
            detail = self._detail(session, survey)
            if not detail.questions:
                raise ErrInvalidInput("A survey must contain at least one question before publication.")
            drafts = [QuestionDraft(q.text, q.type, q.position, q.is_required,
                                   tuple(OptionDraft(o.text, o.position) for o in q.options))
                      for q in detail.questions]
            self._check_questions(drafts)
            if any(q.type != "text" and len(q.options) < 2 for q in detail.questions):
                raise ErrInvalidInput("Choice questions require at least two options before publication.")
            published = session.surveys.publish(survey_id, self._clock())
            return SurveyDetail(**published.model_dump(), questions=detail.questions)
