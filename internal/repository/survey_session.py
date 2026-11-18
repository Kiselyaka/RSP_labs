from contextlib import contextmanager
from collections.abc import Iterator

from internal.database.postgres import Postgres
from internal.repository.postgres import (
    PostgresOptionRepository, PostgresQuestionRepository,
    PostgresSurveyRepository, PostgresUserRepository,
)
from internal.service.survey_session import SurveySession


def session_factory(database: Postgres):
    @contextmanager
    def session() -> Iterator[SurveySession]:
        with database.connection() as connection, connection.transaction():
            @contextmanager
            def provide_connection():
                # Operations share this transaction; only its outer scope commits.
                yield connection

            yield SurveySession(
                users=PostgresUserRepository(provide_connection),
                surveys=PostgresSurveyRepository(provide_connection),
                questions=PostgresQuestionRepository(provide_connection),
                options=PostgresOptionRepository(provide_connection),
            )

    return session
