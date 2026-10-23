import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.security import SESSION_SECRET_MIN_LENGTH, ConfigurationError
from app.main import create_app

REPO_ROOT = Path(__file__).resolve().parent.parent


def settings_with_secret(secret: str) -> Settings:
    return Settings(_env_file=None, SESSION_SECRET=secret)


def test_create_app_fails_without_session_secret():
    with pytest.raises(ConfigurationError, match="SESSION_SECRET is not set"):
        create_app(settings_with_secret(""))


def test_create_app_fails_with_whitespace_session_secret():
    with pytest.raises(ConfigurationError, match="SESSION_SECRET is not set"):
        create_app(settings_with_secret(" " * 40))


def test_create_app_fails_with_short_session_secret():
    short_secret = "s" * (SESSION_SECRET_MIN_LENGTH - 1)
    with pytest.raises(ConfigurationError, match="SESSION_SECRET is too short") as error:
        create_app(settings_with_secret(short_secret))
    assert short_secret not in str(error.value)


def test_create_app_accepts_long_session_secret():
    assert create_app(settings_with_secret("s" * SESSION_SECRET_MIN_LENGTH)) is not None


def test_importing_app_fails_without_session_secret(tmp_path):
    env = {key: value for key, value in os.environ.items() if key != "SESSION_SECRET"}
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["DATABASE_URL"] = f"sqlite:///{tmp_path}/startup.db"

    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "SESSION_SECRET is not set" in result.stderr
