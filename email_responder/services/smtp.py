"""Build and send a threaded plain-text reply using Gmail's SMTP protocol."""

import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

from ..config import Settings
from ..models import IncomingEmail


# Example: receipt = send_reply(settings, email, "Thank you for your email.")
def send_reply(
    settings: Settings, email: IncomingEmail, reply_body: str
) -> dict[str, Any]:
    """Send over an encrypted connection and reject unsuccessful delivery."""

    message = build_message(email, reply_body)
    with smtplib.SMTP_SSL(
        settings.smtp_host,
        settings.smtp_port,
        context=ssl.create_default_context(),
        timeout=30,
    ) as smtp:
        smtp.login(settings.account_email, settings.gmail_app_password)
        refused = smtp.send_message(message)

    if refused:
        raise RuntimeError(f"SMTP refused recipients: {refused}")
    return {"accepted": True, "to": email.sender_email, "subject": email.reply_subject}


# Example: message = build_message(email, "Thanks for getting in touch.")
def build_message(email: IncomingEmail, reply_body: str) -> EmailMessage:
    """Set addresses and reply headers so Gmail keeps the conversation together."""

    message = EmailMessage()
    message["From"] = email.account_email
    message["To"] = email.sender_email
    message["Reply-To"] = email.account_email
    message["Subject"] = email.reply_subject
    if email.message_id:
        message["In-Reply-To"] = email.message_id
        message["References"] = email.message_id
    message.set_content(reply_body)
    return message
