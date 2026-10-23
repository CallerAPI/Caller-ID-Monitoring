import os
import secrets
import tempfile

_test_dir = tempfile.mkdtemp(prefix="caller-id-monitor-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_dir}/test.db"
os.environ["SESSION_SECRET"] = secrets.token_urlsafe(48)

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_lookup_service_factory
from app.db.base import Base, engine
from app.main import app
from app.services import monitor


class FakeLookupService:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_account_info(self):
        return {
            "status": "success",
            "email": "owner@example.com",
            "credits_left": 10,
            "credits_monthly": 10,
            "credits_spent": 0,
        }

    def lookup_number(self, phone_number: str):
        return {
            "status": "success",
            "data": {
                "entity_type": "BUSINESS",
                "business_info": {"business_name": "Example", "city": "Austin", "state": "TX"},
                "is_spam": False,
                "total_complaints": 0,
                "complaints": [],
            },
        }


class FakeScheduler:
    def __init__(self):
        self.jobs = {}

    def add_job(self, func, trigger, args, id, replace_existing):
        self.jobs[id] = args

    def remove_job(self, job_id):
        del self.jobs[job_id]


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def fake_scheduler(monkeypatch):
    scheduler = FakeScheduler()
    monkeypatch.setattr(monitor, "scheduler", scheduler)
    return scheduler


@pytest.fixture(autouse=True)
def fake_lookup_service():
    app.dependency_overrides[get_lookup_service_factory] = lambda: FakeLookupService
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def login():
    def _login(api_key: str) -> TestClient:
        client = TestClient(app)
        response = client.post("/api/v1/auth/confirm", json={"api_key": api_key})
        assert response.status_code == 200, response.text
        return client

    return _login
