from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from internal.domain.errors import ErrConflict, ErrInvalidInput, ErrNotFound
from internal.domain.models import AnswerOption, Question, Survey, User
from internal.service.survey_service import QuestionDraft, SurveyService
from internal.service.survey_session import SurveySession
from internal.service.user_service import UserService

NOW = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)


@pytest.fixture
def setup():
    session = SurveySession(Mock(), Mock(), Mock(), Mock())
    owner = User(id=uuid4(), email="owner@example.test", password_hash="hash",
                 display_name="Owner", created_at=NOW)
    survey = Survey(id=uuid4(), creator_id=owner.id, title="Survey", description=None,
                    status="draft", published_at=None, created_at=NOW)
    question = Question(id=uuid4(), survey_id=survey.id, text="Opinion?", type="text",
                        position=1, is_required=True)
    session.users.get_by_id.return_value = owner
    session.surveys.get_for_update.return_value = survey
    session.surveys.get_by_id.return_value = survey
    session.surveys.create.return_value = survey
    session.questions.for_survey.return_value = [question]
    session.options.for_question.return_value = []
    session.surveys.publish.return_value = survey.model_copy(
        update={"status": "published", "published_at": NOW},
    )

    @contextmanager
    def sessions():
        yield session

    return SurveyService(sessions, lambda: NOW), session, owner, survey


def test_publish_sets_status_and_uses_injected_clock(setup):
    service, session, _, survey = setup
    result = service.publish(survey.id)
    assert result.status == "published" and result.published_at == NOW
    session.surveys.get_for_update.assert_called_once_with(survey.id)
    session.surveys.publish.assert_called_once_with(survey.id, NOW)


def test_empty_survey_cannot_be_published(setup):
    service, session, _, survey = setup
    session.questions.for_survey.return_value = []
    with pytest.raises(ErrInvalidInput, match="at least one question"):
        service.publish(survey.id)
    session.surveys.publish.assert_not_called()


def test_repeat_publication_is_a_conflict(setup):
    service, session, _, survey = setup
    session.surveys.get_for_update.return_value = survey.model_copy(update={"status": "published"})
    with pytest.raises(ErrConflict):
        service.publish(survey.id)
    session.surveys.publish.assert_not_called()


def test_choice_question_requires_two_options(setup):
    service, session, _, survey = setup
    question = session.questions.for_survey.return_value[0]
    session.questions.for_survey.return_value = [question.model_copy(update={"type": "single_choice"})]
    session.options.for_question.return_value = [
        AnswerOption(id=uuid4(), question_id=question.id, text="Only one", position=1),
    ]
    with pytest.raises(ErrInvalidInput, match="at least two options"):
        service.publish(survey.id)
    session.surveys.publish.assert_not_called()


def test_missing_creator_prevents_survey_creation(setup):
    service, session, _, _ = setup
    session.users.get_by_id.side_effect = ErrNotFound("Creator not found")
    with pytest.raises(ErrNotFound):
        service.create(uuid4(), "Valid title", None, [])
    session.surveys.create.assert_not_called()


def test_invalid_title_is_rejected_before_repository_call(setup):
    service, session, owner, _ = setup
    with pytest.raises(ErrInvalidInput):
        service.create(owner.id, "  ", None, [])
    session.surveys.create.assert_not_called()


def test_duplicate_question_positions_are_rejected(setup):
    service, session, owner, _ = setup
    with pytest.raises(ErrInvalidInput, match="positions"):
        service.create(owner.id, "Valid title", None, [
            QuestionDraft("One", "text", 1), QuestionDraft("Two", "text", 1),
        ])
    session.surveys.create.assert_not_called()


def test_user_create_normalizes_and_hashes_password():
    repository = Mock()
    service = UserService(repository)
    service.create(" STUDENT@example.test ", "DemoPassword123", " Student ")
    email, digest, name = repository.create.call_args.args
    assert email == "student@example.test" and name == "Student"
    assert digest.startswith("scrypt$") and "DemoPassword123" not in digest


def test_invalid_user_never_reaches_repository():
    repository = Mock()
    with pytest.raises(ErrInvalidInput):
        UserService(repository).create("wrong", "DemoPassword123", "Student")
    repository.create.assert_not_called()
