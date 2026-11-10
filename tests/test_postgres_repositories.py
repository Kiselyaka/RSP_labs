import os
from contextlib import contextmanager
from uuid import uuid4

import pytest

from internal.config.config import load_config, load_database_config
from internal.database.postgres import Postgres
from internal.domain.errors import ErrAlreadyExists, ErrConflict, ErrInvalidInput, ErrNotFound
from internal.repository.postgres import (
    MAX_PAGE_SIZE,
    PostgresQuestionRepository,
    PostgresSurveyRepository,
    PostgresUserRepository,
)

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="Set RUN_POSTGRES_TESTS=1 and point the DB settings at a migrated test database.",
)


@pytest.fixture(scope="session")
def database():
    load_config()
    db = Postgres()
    try:
        db.open(load_database_config())
        yield db
    finally:
        db.close()


@pytest.fixture
def repositories(database):
    with database.connection() as connection, connection.transaction(force_rollback=True):
        @contextmanager
        def test_connection():
            # Savepoints isolate failed statements and keep the test transaction usable.
            with connection.transaction():
                yield connection

        yield (
            PostgresUserRepository(test_connection),
            PostgresSurveyRepository(test_connection),
            PostgresQuestionRepository(test_connection),
        )


def create_user(users):
    return users.create(f"{uuid4()}@example.test", "test-hash", "Test user")


def test_create_and_read_entities(repositories):
    users, surveys, questions = repositories
    user = create_user(users)
    survey = surveys.create(user.id, "First survey")
    question = questions.create(survey.id, "How was it?", "text", 1)

    assert user.id and user.created_at
    assert survey.id and survey.created_at and survey.status == "draft"
    assert question.id and question.is_required
    assert users.get_by_id(user.id) == users.get_by_email(user.email) == user
    assert surveys.get_by_id(survey.id) == survey
    assert questions.get_by_id(question.id) == question
    assert "password_hash" not in user.model_dump()
    assert "test-hash" not in user.model_dump_json()


def test_missing_record(repositories):
    for repository in repositories:
        with pytest.raises(ErrNotFound):
            repository.get_by_id(uuid4())
        with pytest.raises(ErrNotFound):
            repository.delete(uuid4())


def test_duplicate_and_invalid_data(repositories):
    users, surveys, questions = repositories
    user = create_user(users)
    survey = surveys.create(user.id, "Constraints")
    questions.create(survey.id, "First question", "text", 1)

    with pytest.raises(ErrAlreadyExists):
        users.create(user.email, "other-hash", "Duplicate")
    with pytest.raises(ErrAlreadyExists):
        questions.create(survey.id, "Duplicate position", "text", 1)
    with pytest.raises(ErrInvalidInput):
        questions.create(survey.id, "Invalid position", "text", 0)
    with pytest.raises(ErrInvalidInput):
        surveys.create(user.id, "a" * 201)


def test_ordered_pages_and_limit(repositories):
    users, surveys, questions = repositories
    user = create_user(users)
    survey = surveys.create(user.id, "Pagination")
    for position in range(MAX_PAGE_SIZE + 1, 0, -1):
        questions.create(survey.id, f"Question {position}", "text", position)

    assert [q.position for q in questions.list(2, 0)] == [1, 2]
    assert [q.position for q in questions.list(2, 2)] == [3, 4]
    assert len(questions.list(MAX_PAGE_SIZE + 1, 0)) == MAX_PAGE_SIZE
    assert [u.id for u in users.list(1, 0)] == [user.id]
    assert [s.id for s in surveys.list(1, 0)] == [survey.id]
    with pytest.raises(ErrInvalidInput):
        questions.list(0, 0)
    with pytest.raises(ErrInvalidInput):
        questions.list(10, -1)


def test_update_delete_and_reference_conflict(repositories):
    users, surveys, questions = repositories
    user = create_user(users)
    survey = surveys.create(user.id, "Before update")
    question = questions.create(survey.id, "To delete", "text", 1)
    updated = surveys.update(survey.id, "After update", "New description")
    assert updated.title == "After update" and updated.description == "New description"
    assert surveys.get_by_id(survey.id) == updated
    with pytest.raises(ErrConflict):
        users.delete(user.id)
    for repository, record in ((questions, question), (surveys, survey), (users, user)):
        repository.delete(record.id)
        with pytest.raises(ErrNotFound):
            repository.get_by_id(record.id)
    with pytest.raises(ErrNotFound):
        surveys.update(survey.id, "Missing", None)


def test_email_injection_is_only_a_value(repositories):
    users, _, _ = repositories
    user = create_user(users)
    with pytest.raises(ErrNotFound):
        users.get_by_email("' OR '1'='1' --")
    assert users.get_by_email(user.email).id == user.id
