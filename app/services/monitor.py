import logging
from itertools import groupby
from operator import attrgetter
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from app.db.base import SessionLocal
from app.services.caller_api import CallerAPIService
from app.models.phone_number import PhoneNumber
from app.models.user import User
from app.services.notifications import (
    send_email_notification,
    send_slack_notification,
    send_discord_notification,
    send_telegram_notification,
    send_webhook_notification
)

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def get_owner_api_key(owner_id: int | None, owner: User | None, number_count: int = 1) -> str | None:
    """Return the owner's API key, or log a warning and return None when there is none."""
    if owner_id is None:
        logger.warning("Skipped monitoring for %s phone numbers: the numbers have no owner.", number_count)
        return None
    if owner is None or not owner.api_key:
        logger.warning(
            "Skipped monitoring for %s phone numbers of user id=%s: the user has no API key.",
            number_count,
            owner_id,
        )
        return None
    return owner.api_key


def check_phone_number(phone_number_id: int):
    """Check a single phone number's status with its owner's API key and send notifications if needed"""
    db = SessionLocal()
    try:
        phone_number = db.get(PhoneNumber, phone_number_id)
        if not phone_number or phone_number.disabled:
            return

        owner = db.get(User, phone_number.owner_id) if phone_number.owner_id is not None else None
        api_key = get_owner_api_key(phone_number.owner_id, owner)
        if api_key is None:
            return

        service = CallerAPIService(api_key=api_key)
        result = service.lookup_number(phone_number.number)
        
        # Check if spam status changed
        spam_status_changed = result["is_spam"] != phone_number.is_spam
        reports_increased = result["spam_reports"] > phone_number.spam_reports
        
        if spam_status_changed or reports_increased:
            # Update number status in DB
            phone_number.is_spam = result["is_spam"]
            phone_number.spam_reports = result["spam_reports"]
            db.commit()
            
            # Prepare notification message
            message = f"Alert for {phone_number.number}:\n"
            if spam_status_changed:
                message += f"Spam status changed to: {'SPAM' if result['is_spam'] else 'CLEAN'}\n"
            if reports_increased:
                message += f"New spam reports: {result['spam_reports']}\n"
                
            # Send notifications based on user preferences
            if phone_number.notify_email:
                send_email_notification(phone_number.notify_email, message)
            
            if phone_number.notify_slack:
                send_slack_notification(phone_number.slack_webhook_url, message)
                
            if phone_number.notify_discord:
                send_discord_notification(phone_number.discord_webhook_url, message)
                
            if phone_number.notify_telegram:
                send_telegram_notification(phone_number.telegram_chat_id, message)
                
            if phone_number.notify_webhook:
                send_webhook_notification(phone_number.webhook_url, {
                    "phone_number": phone_number.number,
                    "is_spam": result["is_spam"],
                    "spam_reports": result["spam_reports"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "event": "spam_status_change" if spam_status_changed else "new_reports"
                })
        
        logger.info("Checked phone number id=%s", phone_number_id)
    except Exception as e:
        logger.error("Check failed for phone number id=%s: %s", phone_number_id, type(e).__name__)
    finally:
        db.close()

def add_job_for_number(phone_number_id: int, frequency: int):
    """Add or update a job for a specific phone number"""
    global scheduler
    if not scheduler:
        init_monitoring()
        
    job_id = f"monitor_{phone_number_id}"
    scheduler.add_job(
        check_phone_number,
        trigger=IntervalTrigger(minutes=frequency),
        args=[phone_number_id],
        id=job_id,
        replace_existing=True
    )
    logger.info("Added or updated job for phone number id=%s", phone_number_id)

def remove_job_for_number(phone_number_id: int):
    """Remove the job for a specific phone number"""
    global scheduler
    if scheduler:
        job_id = f"monitor_{phone_number_id}"
        try:
            scheduler.remove_job(job_id)
            logger.info("Removed job for phone number id=%s", phone_number_id)
        except Exception:
            pass  # Job might not exist

def schedule_active_numbers(owner_id: int | None = None) -> int:
    """Schedule active numbers whose owner has an API key. Limit to one owner when owner_id is set."""
    db = SessionLocal()
    try:
        query = db.query(PhoneNumber).filter(PhoneNumber.disabled == False)
        if owner_id is not None:
            query = query.filter(PhoneNumber.owner_id == owner_id)

        scheduled = 0
        numbers = query.order_by(PhoneNumber.owner_id).all()
        for number_owner_id, group in groupby(numbers, key=attrgetter("owner_id")):
            owned_numbers = list(group)
            owner = db.get(User, number_owner_id) if number_owner_id is not None else None
            if get_owner_api_key(number_owner_id, owner, len(owned_numbers)) is None:
                continue
            for number in owned_numbers:
                add_job_for_number(number.id, number.monitoring_frequency)
                scheduled += 1

        logger.info("Monitoring %s phone numbers", scheduled)
        return scheduled
    finally:
        db.close()

def init_monitoring():
    """Initialize the monitoring system - called once at app startup"""
    global scheduler
    if not scheduler:
        scheduler = BackgroundScheduler()
        scheduler.start()
        logger.info("Monitoring scheduler initialized")
