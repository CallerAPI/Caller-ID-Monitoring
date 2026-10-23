import logging

import pytest

from app.core.security import hash_api_key
from app.db.base import SessionLocal
from app.models.phone_number import PhoneNumber
from app.models.user import User
from app.services import monitor

FIRST_KEY = "first-owner-key"
SECOND_KEY = "second-owner-key"


class RecordingLookupService:
    used_keys: list[str] = []

    def __init__(self, api_key: str):
        RecordingLookupService.used_keys.append(api_key)

    def lookup_number(self, phone_number: str):
        return {"is_spam": False, "spam_reports": 0}


@pytest.fixture(autouse=True)
def recording_lookup_service(monkeypatch):
    RecordingLookupService.used_keys = []
    monkeypatch.setattr(monitor, "CallerAPIService", RecordingLookupService)


def add_user(db, api_key: str | None, identity: str) -> User:
    user = User(api_key_hash=hash_api_key(identity), api_key=api_key)
    db.add(user)
    db.commit()
    return user


def add_number(db, owner: User | None, number: str) -> PhoneNumber:
    phone_number = PhoneNumber(owner_id=owner.id if owner else None, number=number)
    db.add(phone_number)
    db.commit()
    return phone_number


def test_check_uses_the_owners_key():
    db = SessionLocal()
    first = add_user(db, FIRST_KEY, "first")
    second = add_user(db, SECOND_KEY, "second")
    first_number = add_number(db, first, "+15125550101")
    second_number = add_number(db, second, "+15125550102")
    first_id, second_id = first_number.id, second_number.id
    db.close()

    monitor.check_phone_number(second_id)
    monitor.check_phone_number(first_id)

    assert RecordingLookupService.used_keys == [SECOND_KEY, FIRST_KEY]


def test_check_skips_owner_without_key_and_logs_safely(caplog):
    db = SessionLocal()
    owner = add_user(db, None, "keyless")
    number = add_number(db, owner, "+15125550103")
    number_id, owner_id = number.id, owner.id
    db.close()

    with caplog.at_level(logging.WARNING, logger=monitor.__name__):
        monitor.check_phone_number(number_id)

    assert RecordingLookupService.used_keys == []
    assert f"user id={owner_id}" in caplog.text
    assert "+15125550103" not in caplog.text


def test_schedule_skips_owners_without_key(fake_scheduler, caplog):
    db = SessionLocal()
    with_key = add_user(db, FIRST_KEY, "with-key")
    without_key = add_user(db, None, "without-key")
    scheduled = add_number(db, with_key, "+15125550104")
    skipped = add_number(db, without_key, "+15125550105")
    orphan = add_number(db, None, "+15125550106")
    scheduled_id, skipped_id, orphan_id = scheduled.id, skipped.id, orphan.id
    db.close()

    with caplog.at_level(logging.WARNING, logger=monitor.__name__):
        assert monitor.schedule_active_numbers() == 1

    assert set(fake_scheduler.jobs) == {f"monitor_{scheduled_id}"}
    assert fake_scheduler.jobs[f"monitor_{scheduled_id}"] == [scheduled_id]
    assert f"monitor_{skipped_id}" not in fake_scheduler.jobs
    assert f"monitor_{orphan_id}" not in fake_scheduler.jobs
    for secret_or_number in (FIRST_KEY, "+15125550105", "+15125550106"):
        assert secret_or_number not in caplog.text


def test_jobs_do_not_carry_api_keys(login, fake_scheduler):
    client = login(FIRST_KEY)
    number_id = client.post("/api/v1/phone-numbers/", json={"number": "+15125550107"}).json()["id"]

    assert fake_scheduler.jobs[f"monitor_{number_id}"] == [number_id]
