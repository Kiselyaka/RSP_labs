from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Generic, TypeVar
from uuid import UUID
from datetime import datetime

from psycopg import Connection, DataError, Error
from psycopg.errors import CheckViolation, ForeignKeyViolation, NotNullViolation, UniqueViolation
from psycopg.rows import class_row
from psycopg_pool import PoolTimeout

from internal.domain.errors import (
    ErrAlreadyExists,
    ErrConflict,
    ErrInvalidInput,
    ErrNotFound,
    RepositoryError,
)
from internal.domain.models import AnswerOption, Question, Survey, User

MAX_PAGE_SIZE = 100
Row = TypeVar("Row")
ConnectionProvider = Callable[[], AbstractContextManager[Connection]]


class _PostgresRepository(Generic[Row]):
    def __init__(self, connection: ConnectionProvider, model: type[Row]) -> None:
        self._connection = connection
        self._model = model

    @contextmanager
    def _connect(self) -> Iterator[Connection]:
        try:
            with self._connection() as connection:
                yield connection
        except UniqueViolation as exc:
            raise ErrAlreadyExists("A record with these unique values already exists.") from exc
        except ForeignKeyViolation as exc:
            raise ErrConflict("The operation conflicts with a related record.") from exc
        except (CheckViolation, NotNullViolation, DataError) as exc:
            raise ErrInvalidInput("The record contains invalid data.") from exc
        except (Error, PoolTimeout) as exc:
            raise RepositoryError("The storage operation failed.") from exc

    def _one(self, query: str, params: tuple[object, ...]) -> Row:
        with self._connect() as connection, connection.cursor(row_factory=class_row(self._model)) as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row is None:
                raise ErrNotFound("Record not found.")
            return row

    def _page(self, query: str, limit: int, offset: int) -> list[Row]:
        if limit < 1 or offset < 0:
            raise ErrInvalidInput("Limit must be positive and offset must be non-negative.")
        with self._connect() as connection, connection.cursor(row_factory=class_row(self._model)) as cursor:
            cursor.execute(query, (min(limit, MAX_PAGE_SIZE), offset))
            return cursor.fetchall()

    def _delete(self, query: str, record_id: UUID) -> None:
        with self._connect() as connection:
            if connection.execute(query, (record_id,)).rowcount == 0:
                raise ErrNotFound("Record not found.")


class PostgresUserRepository(_PostgresRepository[User]):
    def __init__(self, connection: ConnectionProvider) -> None:
        super().__init__(connection, User)

    def create(self, email: str, password_hash: str, display_name: str) -> User:
        return self._one(
            """
            INSERT INTO users (email, password_hash, display_name)
            VALUES (%s, %s, %s)
            RETURNING id, email, password_hash, display_name, created_at
            """,
            (email, password_hash, display_name),
        )

    def get_by_id(self, user_id: UUID) -> User:
        return self._one(
            """
            SELECT id, email, password_hash, display_name, created_at
            FROM users WHERE id = %s
            """,
            (user_id,),
        )

    def get_by_email(self, email: str) -> User:
        return self._one(
            "SELECT id, email, password_hash, display_name, created_at FROM users WHERE email = %s",
            (email,),
        )

    def list(self, limit: int, offset: int) -> list[User]:
        return self._page(
            """
            SELECT id, email, password_hash, display_name, created_at
            FROM users ORDER BY created_at DESC, id LIMIT %s OFFSET %s
            """,
            limit,
            offset,
        )

    def delete(self, user_id: UUID) -> None:
        self._delete("DELETE FROM users WHERE id = %s", user_id)

    def update(self, user_id: UUID, email: str, display_name: str) -> User:
        return self._one(
            """UPDATE users SET email = %s, display_name = %s WHERE id = %s
            RETURNING id, email, password_hash, display_name, created_at""",
            (email, display_name, user_id),
        )


class PostgresSurveyRepository(_PostgresRepository[Survey]):
    def __init__(self, connection: ConnectionProvider) -> None:
        super().__init__(connection, Survey)

    def create(self, creator_id: UUID, title: str, description: str | None = None) -> Survey:
        return self._one(
            """
            INSERT INTO surveys (creator_id, title, description)
            VALUES (%s, %s, %s)
            RETURNING id, creator_id, title, description, status, published_at, created_at
            """,
            (creator_id, title, description),
        )

    def get_by_id(self, survey_id: UUID) -> Survey:
        return self._one(
            """
            SELECT id, creator_id, title, description, status, published_at, created_at
            FROM surveys WHERE id = %s
            """,
            (survey_id,),
        )

    def update(self, survey_id: UUID, title: str, description: str | None) -> Survey:
        return self._one(
            """
            UPDATE surveys SET title = %s, description = %s WHERE id = %s
            RETURNING id, creator_id, title, description, status, published_at, created_at
            """,
            (title, description, survey_id),
        )

    def list(self, limit: int, offset: int) -> list[Survey]:
        return self._page(
            """
            SELECT id, creator_id, title, description, status, published_at, created_at
            FROM surveys ORDER BY created_at DESC, id LIMIT %s OFFSET %s
            """,
            limit,
            offset,
        )

    def delete(self, survey_id: UUID) -> None:
        self._delete("DELETE FROM surveys WHERE id = %s", survey_id)

    def get_for_update(self, survey_id: UUID) -> Survey:
        return self._one(
            """SELECT id, creator_id, title, description, status, published_at, created_at
            FROM surveys WHERE id = %s FOR UPDATE""", (survey_id,),
        )

    def publish(self, survey_id: UUID, published_at: datetime) -> Survey:
        return self._one(
            """UPDATE surveys SET status = 'published', published_at = %s
            WHERE id = %s AND status = 'draft'
            RETURNING id, creator_id, title, description, status, published_at, created_at""",
            (published_at, survey_id),
        )


class PostgresQuestionRepository(_PostgresRepository[Question]):
    def __init__(self, connection: ConnectionProvider) -> None:
        super().__init__(connection, Question)

    def create(
        self, survey_id: UUID, text: str, type: str, position: int, is_required: bool = True,
    ) -> Question:
        return self._one(
            """
            INSERT INTO questions (survey_id, text, type, position, is_required)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, survey_id, text, type, position, is_required
            """,
            (survey_id, text, type, position, is_required),
        )

    def get_by_id(self, question_id: UUID) -> Question:
        return self._one(
            """
            SELECT id, survey_id, text, type, position, is_required
            FROM questions WHERE id = %s
            """,
            (question_id,),
        )

    def list(self, limit: int, offset: int) -> list[Question]:
        return self._page(
            """
            SELECT id, survey_id, text, type, position, is_required
            FROM questions ORDER BY survey_id, position, id LIMIT %s OFFSET %s
            """,
            limit,
            offset,
        )

    def delete(self, question_id: UUID) -> None:
        self._delete("DELETE FROM questions WHERE id = %s", question_id)

    def for_survey(self, survey_id: UUID) -> list[Question]:
        with self._connect() as connection:
            with connection.cursor(row_factory=class_row(Question)) as cursor:
                cursor.execute(
                    """SELECT id, survey_id, text, type, position, is_required
                    FROM questions WHERE survey_id = %s ORDER BY position, id""", (survey_id,),
                )
                return cursor.fetchall()


class PostgresOptionRepository(_PostgresRepository[AnswerOption]):
    def __init__(self, connection: ConnectionProvider) -> None:
        super().__init__(connection, AnswerOption)

    def create(self, question_id: UUID, text: str, position: int) -> AnswerOption:
        return self._one(
            """INSERT INTO answer_options (question_id, text, position) VALUES (%s, %s, %s)
            RETURNING id, question_id, text, position""", (question_id, text, position),
        )

    def for_question(self, question_id: UUID) -> list[AnswerOption]:
        with self._connect() as connection:
            with connection.cursor(row_factory=class_row(AnswerOption)) as cursor:
                cursor.execute(
                    """SELECT id, question_id, text, position FROM answer_options
                    WHERE question_id = %s ORDER BY position, id""", (question_id,),
                )
                return cursor.fetchall()
