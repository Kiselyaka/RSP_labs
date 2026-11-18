from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError

from internal.domain.models import SurveyDetail, User
from internal.service.survey_service import OptionDraft, QuestionDraft


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


Email = Annotated[str, StringConstraints(
    strict=True, strip_whitespace=True, to_lower=True, min_length=3, max_length=255,
    pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
)]
DisplayName = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=2, max_length=100)]
Title = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=3, max_length=200)]
QuestionText = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=1000)]
OptionText = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=500)]
Position = Annotated[int, Field(strict=True, ge=1, le=2147483647)]


class CreateUserRequest(DTO):
    email: Email = Field(examples=["student@example.test"])
    password: str = Field(strict=True, min_length=8, max_length=128, examples=["DemoPassword123"])
    display_name: DisplayName = Field(alias="displayName", examples=["Student"])


class UpdateUserRequest(DTO):
    email: Email
    display_name: DisplayName = Field(alias="displayName")


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
    text: OptionText
    position: Position


class QuestionInput(DTO):
    text: QuestionText
    type: Literal["text", "single_choice", "multiple_choice"]
    position: Position
    is_required: bool = Field(default=True, strict=True, alias="isRequired")
    options: list[OptionInput] = Field(
        default_factory=list, max_length=50,
        description="Must be empty when type is text. Choice questions need two options before publication.",
    )

    @field_validator("options")
    @classmethod
    def options_match_type(cls, options: list[OptionInput], info: ValidationInfo):
        if info.data.get("type") == "text" and options:
            raise PydanticCustomError("text_options", "Text questions cannot contain answer options.")
        return options

    def to_domain(self) -> QuestionDraft:
        return QuestionDraft(self.text, self.type, self.position, self.is_required,
                             tuple(OptionDraft(o.text, o.position) for o in self.options))


class CreateSurveyRequest(DTO):
    creator_id: UUID = Field(alias="creatorId")
    title: Title = Field(examples=["Service feedback"])
    description: str | None = Field(default=None, strict=True, max_length=2000)
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


class FieldIssue(DTO):
    field: str
    issue: str


class ErrorBody(DTO):
    code: str
    message: str
    details: list[FieldIssue] = Field(default_factory=list)
    request_id: UUID = Field(alias="requestId")
    timestamp: datetime


class Error(DTO):
    error: ErrorBody
