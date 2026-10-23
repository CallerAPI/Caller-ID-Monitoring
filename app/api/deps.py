from typing import Callable, Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.models.user import User
from app.services.caller_api import CallerAPIService

SESSION_USER_KEY = "user_id"

LookupServiceFactory = Callable[[str], CallerAPIService]


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_lookup_service_factory() -> LookupServiceFactory:
    return CallerAPIService


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get(SESSION_USER_KEY)
    user = db.get(User, user_id) if isinstance(user_id, int) else None
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_api_key(user: User) -> str:
    if not user.api_key:
        raise HTTPException(status_code=401, detail="No API key is stored for this account. Sign in again.")
    return user.api_key
