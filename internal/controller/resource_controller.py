from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from internal.controller.dto import (
    CreateSurveyRequest, CreateUserRequest, ErrorResponse, SurveyResponse,
    UpdateUserRequest, UserResponse,
)
from internal.service.survey_service import SurveyService
from internal.service.user_service import UserService


def user_service(request: Request) -> UserService:
    return request.app.state.user_service


def survey_service(request: Request) -> SurveyService:
    return request.app.state.survey_service


Users = Annotated[UserService, Depends(user_service)]
Surveys = Annotated[SurveyService, Depends(survey_service)]
router = APIRouter(prefix="/api/v1", responses={
    code: {"model": ErrorResponse, "description": description}
    for code, description in [(400, "Invalid input"), (404, "Resource not found"),
                              (409, "Conflict"), (500, "Internal error")]
})


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             tags=["Users"], responses={201: {"headers": {"Location": {"schema": {"type": "string"}}}}})
def create_user(body: CreateUserRequest, response: Response, service: Users):
    user = service.create(body.email, body.password, body.display_name)
    response.headers["Location"] = f"/api/v1/users/{user.id}"
    return UserResponse.from_domain(user)


@router.get("/users", response_model=list[UserResponse], tags=["Users"])
def list_users(service: Users, limit: int = Query(default=20, ge=1, le=100),
               offset: int = Query(default=0, ge=0)):
    return [UserResponse.from_domain(user) for user in service.list(limit, offset)]


@router.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
def get_user(user_id: UUID, service: Users):
    return UserResponse.from_domain(service.get(user_id))


@router.put("/users/{user_id}", response_model=UserResponse, tags=["Users"])
def update_user(user_id: UUID, body: UpdateUserRequest, service: Users):
    return UserResponse.from_domain(service.update(user_id, body.email, body.display_name))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Users"])
def delete_user(user_id: UUID, service: Users):
    service.delete(user_id)
    return Response(status_code=204)


@router.post("/surveys", response_model=SurveyResponse, status_code=status.HTTP_201_CREATED,
             tags=["Surveys"], responses={201: {"headers": {"Location": {"schema": {"type": "string"}}}}})
def create_survey(body: CreateSurveyRequest, response: Response, service: Surveys):
    survey = service.create(body.creator_id, body.title, body.description,
                            [q.to_domain() for q in body.questions])
    response.headers["Location"] = f"/api/v1/surveys/{survey.id}"
    return SurveyResponse.from_domain(survey)


@router.get("/surveys/{survey_id}", response_model=SurveyResponse, tags=["Surveys"])
def get_survey(survey_id: UUID, service: Surveys):
    return SurveyResponse.from_domain(service.get(survey_id))


@router.post("/surveys/{survey_id}/publish", response_model=SurveyResponse, tags=["Surveys"])
def publish_survey(survey_id: UUID, service: Surveys):
    return SurveyResponse.from_domain(service.publish(survey_id))
