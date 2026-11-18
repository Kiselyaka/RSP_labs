from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class User(BaseModel):
    id: UUID
    email: str
    password_hash: str = Field(exclude=True, repr=False)
    display_name: str
    created_at: datetime


class Survey(BaseModel):
    id: UUID
    creator_id: UUID
    title: str
    description: str | None
    status: str
    published_at: datetime | None
    created_at: datetime


class Question(BaseModel):
    id: UUID
    survey_id: UUID
    text: str
    type: str
    position: int
    is_required: bool


class AnswerOption(BaseModel):
    id: UUID
    question_id: UUID
    text: str
    position: int


class QuestionDetail(Question):
    options: list[AnswerOption]


class SurveyDetail(Survey):
    questions: list[QuestionDetail]
