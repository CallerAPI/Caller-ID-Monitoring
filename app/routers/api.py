from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.api.deps import (
    LookupServiceFactory,
    get_current_user,
    get_db,
    get_lookup_service_factory,
    require_api_key,
)
from app.models.notifications import NotificationSettings
from app.models.user import User
from pydantic import BaseModel

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
def get_account_info(
    current_user: User = Depends(get_current_user),
    service_factory: LookupServiceFactory = Depends(get_lookup_service_factory),
):
    api_key = require_api_key(current_user)
    
    try:
        service = service_factory(api_key)
        account_info = service.get_account_info()
        account_info["api_key"] = api_key  # The settings page shows the user's own key
        return account_info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/settings/notifications")
def save_notification_settings(
    settings: NotificationSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = require_api_key(current_user)
    
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
def get_notification_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = require_api_key(current_user)
    
    # Get settings from DB, return defaults if not found
    settings = db.query(NotificationSettings).filter(
        NotificationSettings.api_key == api_key
    ).first()
    
    if not settings:
        return NotificationSettingsUpdate().dict()
    
    return NotificationSettingsUpdate.model_validate(settings).dict()
