from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import logging
import json
from uuid import UUID, uuid4

import pytest

from internal.controller.request_context import RequestLogFormatter, request_id
from internal.domain.errors import ErrInvalidInput, ErrNotFound, RepositoryError
from test_http import client


def error_of(response, code, status=400):
    assert response.status_code == status
    body = response.json()["error"]
    assert body["code"] == code
    assert body["requestId"] == response.headers["x-request-id"]
    UUID(body["requestId"])
    assert datetime.fromisoformat(body["timestamp"].replace("Z", "+00:00")).utcoffset().total_seconds() == 0
    assert isinstance(body["details"], list)
    return body


def user_body():
    return {"email": "student@example.test", "password": "DemoPassword123", "displayName": "Student"}


def survey_body():
    return {"creatorId": str(uuid4()), "title": "Valid survey", "questions": [
        {"text": "Question?", "type": "text", "position": 1, "isRequired": True},
    ]}


def test_all_invalid_fields_are_reported_without_values(client):
    http, users, _ = client
    response = http.post("/api/v1/users", json={"email": "wrong", "password": "secret", "displayName": " "})
    body = error_of(response, "VALIDATION_ERROR")
    assert {issue["field"] for issue in body["details"]} == {"email", "password", "displayName"}
    assert "secret" not in response.text and "wrong" not in response.text
    users.create.assert_not_called()


def test_cross_field_type_and_options(client):
    http, _, surveys = client
    data = survey_body()
    data["questions"][0]["options"] = [{"text": "Not for text question", "position": 1}]
    body = error_of(http.post("/api/v1/surveys", json=data), "VALIDATION_ERROR")
    assert body["details"][0]["field"] == "questions[0].options"
    surveys.create.assert_not_called()


@pytest.mark.parametrize("method,path,data", [
    ("POST", "/api/v1/users", {**user_body(), "role": "admin"}),
    ("PUT", f"/api/v1/users/{uuid4()}", {"email": "a@example.test", "displayName": "Student", "role": "admin"}),
    ("POST", "/api/v1/surveys", {**survey_body(), "status": "published"}),
])
def test_unknown_fields_are_rejected(client, method, path, data):
    http, _, _ = client
    body = error_of(http.request(method, path, json=data), "MALFORMED_JSON")
    assert any(issue["issue"] == "Unknown field." for issue in body["details"])


def test_syntactically_invalid_json(client):
    http, users, _ = client
    response = http.post("/api/v1/users", content='{"email":', headers={"Content-Type": "application/json"})
    error_of(response, "MALFORMED_JSON")
    users.create.assert_not_called()


@pytest.mark.parametrize("position", ["1", True, 1.5])
def test_json_number_types_are_not_coerced(client, position):
    http, _, _ = client
    data = survey_body()
    data["questions"][0]["position"] = position
    body = error_of(http.post("/api/v1/surveys", json=data), "MALFORMED_JSON")
    assert body["details"][0]["field"] == "questions[0].position"


@pytest.mark.parametrize("params,field", [
    ({"limit": 1000}, "limit"), ({"limit": 0}, "limit"),
    ({"offset": -1}, "offset"), ({"limit": "wrong"}, "limit"),
])
def test_query_validation_names_the_field(client, params, field):
    http, users, _ = client
    body = error_of(http.get("/api/v1/users", params=params), "VALIDATION_ERROR")
    assert field in {issue["field"] for issue in body["details"]}
    users.list.assert_not_called()


def test_uuid_validation(client):
    http, _, _ = client
    body = error_of(http.get("/api/v1/users/abc"), "VALIDATION_ERROR")
    assert body["details"][0]["field"] == "user_id"


def test_service_business_rule_stays_invalid_input(client):
    http, _, surveys = client
    surveys.publish.side_effect = ErrInvalidInput("Survey must contain a question.")
    body = error_of(http.post(f"/api/v1/surveys/{uuid4()}/publish"), "INVALID_INPUT")
    assert body["details"] == []


def test_unknown_route_has_common_not_found_format(client):
    http, _, _ = client
    error_of(http.get("/api/v1/unknown"), "NOT_FOUND", 404)


def test_missing_resource_has_common_not_found_format(client):
    http, users, _ = client
    users.get.side_effect = ErrNotFound("User not found.")
    error_of(http.get(f"/api/v1/users/{uuid4()}"), "NOT_FOUND", 404)


def test_method_not_allowed_keeps_allow_header(client):
    http, _, _ = client
    response = http.patch(f"/api/v1/users/{uuid4()}", json={})
    error_of(response, "METHOD_NOT_ALLOWED", 405)
    assert "allow" in response.headers


@pytest.mark.parametrize("failure", [RuntimeError('SQL SELECT secret_column FROM private_table'),
                                      RepositoryError('database connection failed')])
def test_500_is_safe_and_correlated_with_full_log(client, caplog, failure):
    http, users, _ = client
    users.get.side_effect = failure
    with caplog.at_level(logging.INFO):
        response = http.get(f"/api/v1/users/{uuid4()}")
    body = error_of(response, "INTERNAL_ERROR", 500)
    assert body["message"] == "An internal error occurred." and body["details"] == []
    assert str(failure) not in response.text
    errors = [record for record in caplog.records if record.exc_info]
    assert any(record.requestId == body["requestId"] and record.exc_info[1] is failure for record in errors)
    assert any(getattr(record, "requestId", None) == body["requestId"] and "status=500" in record.getMessage()
               for record in caplog.records)


def test_request_ids_are_unique_and_not_client_controlled(client):
    http, _, _ = client
    identifiers = set()
    for _ in range(3):
        response = http.get("/docs", headers={"X-Request-ID": "spoofed"})
        assert response.status_code == 200
        identifier = response.headers["x-request-id"]
        UUID(identifier)
        identifiers.add(identifier)
    assert len(identifiers) == 3
    assert request_id.get() == "-"


def test_concurrent_requests_keep_their_ids(client):
    http, _, _ = client
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: http.get("/missing"), range(8)))
    identifiers = {error_of(response, "NOT_FOUND", 404)["requestId"] for response in responses}
    assert len(identifiers) == 8


@pytest.mark.parametrize("data,expected", [
    ({"email": "student@example.test", "displayName": "Student"}, "password"),
    ({"password": "DemoPassword123", "displayName": "Student"}, "email"),
])
def test_required_fields_are_distinct_from_defaults(client, data, expected):
    http, _, _ = client
    body = error_of(http.post("/api/v1/users", json=data), "VALIDATION_ERROR")
    assert any(issue["field"] == expected and issue["issue"] == "Field is required." for issue in body["details"])


def test_missing_numeric_field_and_zero_are_different(client):
    http, _, _ = client
    data = survey_body()
    del data["questions"][0]["position"]
    missing = error_of(http.post("/api/v1/surveys", json=data), "VALIDATION_ERROR")
    data["questions"][0]["position"] = 0
    zero = error_of(http.post("/api/v1/surveys", json=data), "VALIDATION_ERROR")
    assert missing["details"][0]["issue"] == "Field is required."
    assert zero["details"][0]["issue"] != "Field is required."


def test_log_formatter_keeps_one_json_line_with_request_id():
    record = logging.LogRecord("test", logging.ERROR, __file__, 1, "message\nsecond line", (), None)
    record.requestId = str(uuid4())
    rendered = RequestLogFormatter().format(record)
    assert "\n" not in rendered
    body = json.loads(rendered)
    assert body["requestId"] == record.requestId and body["message"] == "message\nsecond line"
