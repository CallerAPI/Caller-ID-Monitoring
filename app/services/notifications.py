import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
import os

def send_email_notification(to_email: str, message: str):
    """Send email notification using SMTP"""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    from_email = os.getenv("FROM_EMAIL")
    
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = "CallerAPI Alert"
    
    msg.attach(MIMEText(message, "plain"))
    
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

def send_slack_notification(webhook_url: str, message: str):
    """Send notification to Slack"""
    requests.post(webhook_url, json={"text": message})

def send_discord_notification(webhook_url: str, message: str):
    """Send notification to Discord"""
    requests.post(webhook_url, json={"content": message})

def send_telegram_notification(chat_id: str, message: str):
    """Send notification via Telegram"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ValueError("Telegram bot token not configured")
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    })

def send_webhook_notification(webhook_url: str, data: Dict[str, Any]):
    """Send notification to custom webhook"""
    secret = os.getenv("WEBHOOK_SECRET")
    headers = {"X-Webhook-Secret": secret} if secret else {}
    
    requests.post(webhook_url, json=data, headers=headers) 