from sqlalchemy import Column, Boolean, String
from app.db.base import Base

class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    api_key = Column(String, primary_key=True)
    notify_email = Column(Boolean, default=False)
    notify_slack = Column(Boolean, default=False)
    slack_webhook_url = Column(String, default="")
    notify_discord = Column(Boolean, default=False)
    discord_webhook_url = Column(String, default="")
    notify_telegram = Column(Boolean, default=False)
    telegram_chat_id = Column(String, default="")
    notify_webhook = Column(Boolean, default=False)
    webhook_url = Column(String, default="") 