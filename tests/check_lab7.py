"""Acceptance checks against a running API on a disposable migrated database."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8080/api/v1")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = []

    def request(method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = Request(args.base + path, method=method, data=data,
                      headers={"Content-Type": "application/json"})
        try:
            response = urlopen(req, timeout=15)
        except HTTPError as exc:
            response = exc
        with response:
            payload = response.read()
            return response.status, {k.lower(): v for k, v in response.headers.items()}, json.loads(payload) if payload else None

    def check(name, response, expected):
        status, headers, body = response
        assert status == expected, (name, status, body)
        results.append({"check": name, "status": status, "headers": headers, "body": body})
        print(f"PASS {name}: HTTP {status}")
        return body

    token = uuid4().hex[:10]
    user_body = {"email": f"lab7-{token}@example.test", "password": "DemoPassword123",
                 "displayName": "Lab 7 owner"}
    created = request("POST", "/users", user_body)
    owner = check("P1 create user and Location", created, 201)
    assert created[1].get("location") == f"/api/v1/users/{owner['id']}"
    assert "password" not in json.dumps(owner).lower()
    page = check("P2 list limit=2", request("GET", "/users?limit=2&offset=0"), 200)
    assert len(page) <= 2
    updated = check("P3 PUT user", request("PUT", f"/users/{owner['id']}", {
        "email": owner["email"], "displayName": "Updated owner",
    }), 200)
    assert updated["displayName"] == "Updated owner" and updated["id"] == owner["id"]
    check("P4 unknown user", request("GET", f"/users/{uuid4()}"), 404)
    check("invalid UUID", request("GET", "/users/invalid"), 400)
    check("duplicate email", request("POST", "/users", user_body), 409)
    survey_body = {"creatorId": owner["id"], "title": "Lab 7 survey", "questions": [
        {"text": "Your opinion?", "type": "text", "position": 1, "isRequired": True},
    ]}
    created_survey = request("POST", "/surveys", survey_body)
    survey = check("P5 create survey", created_survey, 201)
    assert created_survey[1].get("location") == f"/api/v1/surveys/{survey['id']}"
    check("read survey", request("GET", f"/surveys/{survey['id']}"), 200)
    check("missing creator", request("POST", "/surveys", {**survey_body, "creatorId": str(uuid4())}), 404)
    check("P6 invalid title", request("POST", "/surveys", {**survey_body, "title": " "}), 400)
    empty = check("create empty draft", request("POST", "/surveys", {
        "creatorId": owner["id"], "title": "Empty draft",
    }), 201)
    check("P6 publish empty draft", request("POST", f"/surveys/{empty['id']}/publish"), 400)
    published = check("P8 publish draft", request("POST", f"/surveys/{survey['id']}/publish"), 200)
    assert published["status"] == "published" and published["publishedAt"]
    check("P7 P8 repeat publication", request("POST", f"/surveys/{survey['id']}/publish"), 409)
    check("related user delete conflict", request("DELETE", f"/users/{owner['id']}"), 409)
    choice = check("create incomplete choice draft", request("POST", "/surveys", {
        "creatorId": owner["id"], "title": "Choice draft", "questions": [
            {"text": "Choose", "type": "single_choice", "position": 1,
             "options": [{"text": "One", "position": 1}]},
        ],
    }), 201)
    check("P6 choice requires two options", request("POST", f"/surveys/{choice['id']}/publish"), 400)
    free_user = check("create unlinked user", request("POST", "/users", {
        **user_body, "email": f"free-{token}@example.test",
    }), 201)
    removed = request("DELETE", f"/users/{free_user['id']}")
    check("P9 delete unlinked user", removed, 204)
    assert removed[2] is None
    check("read deleted user", request("GET", f"/users/{free_user['id']}"), 404)
    race = check("create concurrency draft", request("POST", "/surveys", survey_body), 201)
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = sorted(r[0] for r in pool.map(
            lambda _: request("POST", f"/surveys/{race['id']}/publish"), range(2),
        ))
    assert codes == [200, 409], codes
    results.append({"check": "concurrent publication", "statuses": codes})
    print("PASS concurrent publication: one 200 and one 409")
    if args.output:
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"All {len(results)} acceptance checks passed.")


if __name__ == "__main__":
    main()
