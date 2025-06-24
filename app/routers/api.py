from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from app.services.caller_api import CallerAPIService
from app.models.notifications import NotificationSettings
from app.db.base import SessionLocal
from pydantic import BaseModel

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic model for request validation
class NotificationSettingsUpdate(BaseModel):
    notify_email: bool = False
    notify_slack: bool = False
    slack_webhook_url: str = ""
    notify_discord: bool = False
    discord_webhook_url: str = ""
    notify_telegram: bool = False
    telegram_chat_id: str = ""
    notify_webhook: bool = False
    webhook_url: str = ""

    class Config:
        from_attributes = True

router = APIRouter(prefix="/api/v1")

@router.get("/me")
async def get_account_info(request: Request):
    api_key = request.session.get("api_key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        service = CallerAPIService(api_key=api_key)
        account_info = service.get_account_info()
        account_info["api_key"] = api_key  # Add API key from session to response
        return account_info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/settings/notifications")
async def save_notification_settings(
    settings: NotificationSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    api_key = request.session.get("api_key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get existing settings or create new
    db_settings = db.query(NotificationSettings).filter(
        NotificationSettings.api_key == api_key
    ).first()
    
    if not db_settings:
        db_settings = NotificationSettings(api_key=api_key)
        db.add(db_settings)
    
    # Update settings
    for key, value in settings.dict().items():
        setattr(db_settings, key, value)
    
    try:
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/settings/notifications")
async def get_notification_settings(request: Request, db: Session = Depends(get_db)):
    api_key = request.session.get("api_key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get settings from DB, return defaults if not found
    settings = db.query(NotificationSettings).filter(
        NotificationSettings.api_key == api_key
    ).first()
    
    if not settings:
        return NotificationSettingsUpdate().dict()
    
    return settings 
