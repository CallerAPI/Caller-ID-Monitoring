from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.deps import SESSION_USER_KEY, LookupServiceFactory, get_db, get_lookup_service_factory
from app.core.security import hash_api_key
from app.models.user import User
from app.services.monitor import schedule_active_numbers

router = APIRouter(prefix="/api/v1/auth")

class ApiKeyVerification(BaseModel):
    api_key: str

@router.post("/verify")
async def verify_api_key(
    verification: ApiKeyVerification,
    service_factory: LookupServiceFactory = Depends(get_lookup_service_factory),
):
    try:
        service = service_factory(verification.api_key)
        account_info = service.get_account_info()
        return account_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confirm")
def confirm_account(
    request: Request,
    verification: ApiKeyVerification,
    db: Session = Depends(get_db),
    service_factory: LookupServiceFactory = Depends(get_lookup_service_factory),
):
    try:
        # Verify one more time to ensure the key is still valid
        service = service_factory(verification.api_key)
        service.get_account_info()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    key_hash = hash_api_key(verification.api_key)
    user = db.query(User).filter(User.api_key_hash == key_hash).first()
    if user is None:
        user = User(api_key_hash=key_hash)
        db.add(user)
    user.api_key = verification.api_key
    db.commit()
    db.refresh(user)

    request.session.clear()
    request.session[SESSION_USER_KEY] = user.id

    schedule_active_numbers(owner_id=user.id)

    return {"status": "success"}
