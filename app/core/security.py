import hashlib

SESSION_SECRET_MIN_LENGTH = 32


class ConfigurationError(RuntimeError):
    pass


def require_session_secret(value: str | None) -> str:
    secret = (value or "").strip()
    if not secret:
        raise ConfigurationError(
            "SESSION_SECRET is not set. Set SESSION_SECRET to a random value of at least "
            f"{SESSION_SECRET_MIN_LENGTH} characters before you start the app. To make a value, run: "
            "python -c 'import secrets; print(secrets.token_urlsafe(48))'"
        )
    if len(secret) < SESSION_SECRET_MIN_LENGTH:
        raise ConfigurationError(
            f"SESSION_SECRET is too short. Use a random value of at least {SESSION_SECRET_MIN_LENGTH} characters."
        )
    return secret


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()
