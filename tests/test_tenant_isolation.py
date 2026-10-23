import base64
import json

import itsdangerous
from fastapi.testclient import TestClient

from app.main import app

NUMBER = "+15125550100"


def create_number(client: TestClient, number: str = NUMBER) -> int:
    response = client.post("/api/v1/phone-numbers/", json={"number": number})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_second_user_cannot_list_first_users_numbers(login):
    first = login("first-user-key")
    second = login("second-user-key")
    create_number(first)

    assert [n["number"] for n in first.get("/api/v1/phone-numbers/").json()] == [NUMBER]
    assert second.get("/api/v1/phone-numbers/").json() == []


def test_second_user_cannot_read_first_users_number(login):
    first = login("first-user-key")
    second = login("second-user-key")
    number_id = create_number(first)

    assert first.get(f"/api/v1/phone-numbers/{number_id}").status_code == 200
    response = second.get(f"/api/v1/phone-numbers/{number_id}")
    assert response.status_code == 404
    assert NUMBER not in response.text


def test_second_user_cannot_update_first_users_number(login):
    first = login("first-user-key")
    second = login("second-user-key")
    number_id = create_number(first)

    response = second.patch(f"/api/v1/phone-numbers/{number_id}", json={"disabled": True})
    assert response.status_code == 404
    assert first.get(f"/api/v1/phone-numbers/{number_id}").json()["disabled"] is False


def test_second_user_cannot_delete_first_users_number(login, fake_scheduler):
    first = login("first-user-key")
    second = login("second-user-key")
    number_id = create_number(first)

    assert second.delete(f"/api/v1/phone-numbers/{number_id}").status_code == 404
    assert f"monitor_{number_id}" in fake_scheduler.jobs
    assert [n["id"] for n in first.get("/api/v1/phone-numbers/").json()] == [number_id]

    assert first.delete(f"/api/v1/phone-numbers/{number_id}").status_code == 200
    assert first.get("/api/v1/phone-numbers/").json() == []


def test_duplicate_check_is_per_user(login):
    first = login("first-user-key")
    second = login("second-user-key")
    create_number(first)

    create_number(second)
    assert first.post("/api/v1/phone-numbers/", json={"number": NUMBER}).status_code == 400
    assert len(second.get("/api/v1/phone-numbers/").json()) == 1


def test_same_key_signs_in_to_same_user(login):
    first = login("first-user-key")
    number_id = create_number(first)

    again = login("first-user-key")
    assert [n["id"] for n in again.get("/api/v1/phone-numbers/").json()] == [number_id]


def test_requests_without_session_are_rejected():
    client = TestClient(app)
    assert client.get("/api/v1/phone-numbers/").status_code == 401
    assert client.get("/api/v1/phone-numbers/1").status_code == 401
    assert client.delete("/api/v1/phone-numbers/1").status_code == 401
    assert client.get("/api/v1/me").status_code == 401
    assert client.get("/api/v1/settings/notifications").status_code == 401


def test_session_signed_with_other_secret_is_rejected(login):
    login("first-user-key")
    forged = TestClient(app)
    forged.cookies.set("session", _forged_session_cookie({"user_id": 1}))
    assert forged.get("/api/v1/phone-numbers/").status_code == 401


def test_notification_settings_are_per_user(login):
    first = login("first-user-key")
    second = login("second-user-key")
    payload = {"notify_slack": True, "slack_webhook_url": "https://hooks.example.com/first"}
    assert first.post("/api/v1/settings/notifications", json=payload).status_code == 200

    assert first.get("/api/v1/settings/notifications").json()["slack_webhook_url"] == payload["slack_webhook_url"]
    assert second.get("/api/v1/settings/notifications").json()["slack_webhook_url"] == ""


def _forged_session_cookie(data: dict) -> str:
    signer = itsdangerous.TimestampSigner("not-the-real-session-secret-0123456789")
    return signer.sign(base64.b64encode(json.dumps(data).encode())).decode()
