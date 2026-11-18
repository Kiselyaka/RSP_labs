from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from internal.domain.models import SurveyDetail, User
from internal.service.survey_service import OptionDraft, QuestionDraft


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class CreateUserRequest(DTO):
    email: str = Field(max_length=255, examples=["student@example.test"])
    password: str = Field(min_length=8, max_length=128, examples=["DemoPassword123"])
    display_name: str = Field(alias="displayName", max_length=100, examples=["Student"])


class UpdateUserRequest(DTO):
    email: str = Field(max_length=255)
    display_name: str = Field(alias="displayName", max_length=100)


class UserResponse(DTO):
    id: UUID
    email: str
    display_name: str = Field(alias="displayName")
    created_at: datetime = Field(alias="createdAt")

    @classmethod
    def from_domain(cls, user: User):
        return cls(id=user.id, email=user.email, display_name=user.display_name,
                   created_at=user.created_at)


class OptionInput(DTO):
    text: str = Field(max_length=500)
    position: int


class QuestionInput(DTO):
    text: str = Field(max_length=1000)
    type: Literal["text", "single_choice", "multiple_choice"]
    position: int
    is_required: bool = Field(default=True, alias="isRequired")
    options: list[OptionInput] = Field(default_factory=list, max_length=50)

    def to_domain(self) -> QuestionDraft:
        return QuestionDraft(self.text, self.type, self.position, self.is_required,
                             tuple(OptionDraft(o.text, o.position) for o in self.options))


class CreateSurveyRequest(DTO):
    creator_id: UUID = Field(alias="creatorId")
    title: str = Field(max_length=200, examples=["Service feedback"])
    description: str | None = Field(default=None, max_length=2000)
    questions: list[QuestionInput] = Field(default_factory=list, max_length=100)


class OptionResponse(OptionInput):
    id: UUID


class QuestionResponse(DTO):
    id: UUID
    text: str
    type: Literal["text", "single_choice", "multiple_choice"]
    position: int
    is_required: bool = Field(alias="isRequired")
    options: list[OptionResponse]


class SurveyResponse(DTO):
    id: UUID
    creator_id: UUID = Field(alias="creatorId")
    title: str
    description: str | None
    status: Literal["draft", "published", "closed"]
    published_at: datetime | None = Field(alias="publishedAt")
    created_at: datetime = Field(alias="createdAt")
    question_count: int = Field(alias="questionCount")
    questions: list[QuestionResponse]

    @classmethod
    def from_domain(cls, survey: SurveyDetail):
        questions = [QuestionResponse(
            id=q.id, text=q.text, type=q.type, position=q.position, is_required=q.is_required,
            options=[OptionResponse(id=o.id, text=o.text, position=o.position) for o in q.options],
        ) for q in survey.questions]
        return cls(id=survey.id, creator_id=survey.creator_id, title=survey.title,
                   description=survey.description, status=survey.status,
                   published_at=survey.published_at, created_at=survey.created_at,
                   question_count=len(questions), questions=questions)


class ErrorResponse(DTO):
    code: str
    message: str
    timestamp: datetime
