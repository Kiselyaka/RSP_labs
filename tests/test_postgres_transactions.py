"""Regression check for partial survey creation, enabled only for a test database."""
import os
from uuid import uuid4

import pytest

from internal.config.config import load_config, load_database_config
from internal.database.postgres import Postgres
from internal.domain.errors import ErrInvalidInput
from internal.repository.postgres import PostgresOptionRepository, PostgresUserRepository
from internal.repository.survey_session import session_factory
from internal.service.survey_service import OptionDraft, QuestionDraft, SurveyService

pytestmark = pytest.mark.skipif(os.getenv("RUN_POSTGRES_TESTS") != "1",
                                reason="Requires a migrated test PostgreSQL database.")


def test_failed_option_insert_rolls_back_survey_and_question(monkeypatch):
    load_config()
    database = Postgres()
    database.open(load_database_config())
    owner = None
    try:
        owner = PostgresUserRepository(database.connection).create(
            f"atomic-{uuid4()}@example.test", "test-hash", "Atomic test",
        )
        original_create = PostgresOptionRepository.create

        def fail_at_database(repository, question_id, text, position):
            return original_create(repository, question_id, text, 0)

        monkeypatch.setattr(PostgresOptionRepository, "create", fail_at_database)
        service = SurveyService(session_factory(database))
        with pytest.raises(ErrInvalidInput):
            service.create(owner.id, "Atomic survey", None, [
                QuestionDraft("Choice?", "single_choice", 1, True,
                              (OptionDraft("Yes", 1), OptionDraft("No", 2))),
            ])
        with database.connection() as connection:
            assert connection.execute(
                "SELECT count(*) FROM surveys WHERE creator_id = %s", (owner.id,),
            ).fetchone()[0] == 0
    finally:
        if owner is not None:
            with database.connection() as connection:
                connection.execute("DELETE FROM surveys WHERE creator_id = %s", (owner.id,))
                connection.execute("DELETE FROM users WHERE id = %s", (owner.id,))
        database.close()
