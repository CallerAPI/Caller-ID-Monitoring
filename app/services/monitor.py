from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.base import SessionLocal
from app.services.caller_api import CallerAPIService
from app.models.phone_number import PhoneNumber
from app.services.notifications import (
    send_email_notification,
    send_slack_notification,
    send_discord_notification,
    send_telegram_notification,
    send_webhook_notification
)

# Global scheduler instance
scheduler = None
current_api_key = None

def check_phone_number(phone_number_id: int, api_key: str, db: Session):
    """Check a single phone number's status and send notifications if needed"""
    try:
        # Get phone number from DB
        phone_number = db.query(PhoneNumber).filter(PhoneNumber.id == phone_number_id).first()
        if not phone_number or phone_number.disabled:
            return
            
        # Check number status using the API key from session
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
        
        print(f"Checked phone number {phone_number.number}")
    except Exception as e:
        print(f"Error checking phone number {phone_number_id}: {str(e)}")

def add_job_for_number(phone_number_id: int, frequency: int, api_key: str):
    """Add or update a job for a specific phone number"""
    global scheduler
    if not scheduler:
        init_monitoring()
        
    job_id = f"monitor_{phone_number_id}"
    scheduler.add_job(
        check_phone_number,
        trigger=IntervalTrigger(minutes=frequency),
        args=[phone_number_id, api_key, SessionLocal()],
        id=job_id,
        replace_existing=True
    )
    print(f"Added/updated job for phone number {phone_number_id}")

def remove_job_for_number(phone_number_id: int):
    """Remove the job for a specific phone number"""
    global scheduler
    if scheduler:
        job_id = f"monitor_{phone_number_id}"
        try:
            scheduler.remove_job(job_id)
            print(f"Removed job for phone number {phone_number_id}")
        except:
            pass  # Job might not exist

def set_api_key(api_key: str):
    """Set the API key and start monitoring for all active numbers"""
    global current_api_key, scheduler
    
    if api_key == current_api_key:
        return  # No change needed
        
    current_api_key = api_key
    
    if not scheduler:
        init_monitoring()
    
    db = SessionLocal()
    try:
        # Get all active phone numbers
        phone_numbers = db.query(PhoneNumber).filter(PhoneNumber.disabled == False).all()
        
        # Update/add jobs for all active numbers
        for number in phone_numbers:
            add_job_for_number(number.id, number.monitoring_frequency, api_key)
            
        print(f"Monitoring {len(phone_numbers)} phone numbers")
    finally:
        db.close()

def init_monitoring():
    """Initialize the monitoring system - called once at app startup"""
    global scheduler
    if not scheduler:
        scheduler = BackgroundScheduler()
        scheduler.start()
        print("Monitoring scheduler initialized") 