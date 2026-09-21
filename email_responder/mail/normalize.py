"""Turn one parsed message into the plain email object used by the workflow.

Read normalize_message first; MIME decoding and message hashing live next door.
"""

import re
from datetime import UTC
from email.message import Message
from email.utils import parseaddr

from ..config import Settings
from ..models import IncomingEmail
from ..text import normalize_text, normalize_whitespace
from .filtering import blocked_sender_reason
from .identity import workflow_hash
from .parsing import extract_bodies, parse_received_date


# Example: payload = normalize_message(message, 42, settings)
def normalize_message(
    message: Message, imap_uid: int | None, settings: Settings
) -> IncomingEmail | None:
    """Convert a parsed email message into the workflow's normalized shape."""

    sender_raw = normalize_whitespace(str(message.get("From", "")))
    sender_email = parseaddr(sender_raw)[1].lower()
    if not sender_email:
        raise ValueError("Incoming email did not include a parseable From address.")
    if sender_email == settings.account_email:
        return None

    skip_information = blocked_sender_reason(sender_email, sender_raw, settings)
    plain_body, html_body = extract_bodies(message)
    email_text = normalize_whitespace(plain_body) or normalize_text(html_body)
    if not email_text and not skip_information:
        raise ValueError(
            "Incoming email did not include a plain-text or HTML body to answer."
        )

    original_subject = normalize_whitespace(str(message.get("Subject", "")))
    if not original_subject:
        original_subject = "(no subject)"
    reply_subject = (
        original_subject
        if re.match(r"^\s*re:", original_subject, flags=re.IGNORECASE)
        else f"Re: {original_subject}"
    )

    message_id = normalize_whitespace(str(message.get("Message-ID", "")))
    received_at = parse_received_date(message.get("Date")).astimezone(UTC)
    received_at_text = received_at.isoformat()
    fallback_source = "\n".join(
        [sender_email, received_at_text, original_subject, email_text]
    )
    message_key = message_id or (
        f"imap-uid:{imap_uid if imap_uid is not None else 'none'}:"
        f"{workflow_hash(fallback_source)}"
    )
    to_raw = normalize_whitespace(str(message.get("To", settings.account_email)))
    cc_raw = normalize_whitespace(str(message.get("Cc", "")))
    full_email = "\n".join(
        [
            f"From: {sender_raw or sender_email}",
            f"To: {to_raw or settings.account_email}",
            f"Date: {received_at_text}",
            f"Subject: {original_subject}",
            "",
            email_text,
        ]
    )

    return IncomingEmail(
        mailbox=settings.account_email,
        account_email=settings.account_email,
        sender_email=sender_email,
        sender_raw=sender_raw or sender_email,
        to_raw=to_raw or settings.account_email,
        cc_raw=cc_raw,
        received_at=received_at_text,
        message_id=message_id,
        message_key=message_key,
        original_subject=original_subject,
        reply_subject=reply_subject,
        email_text=email_text,
        full_email=full_email,
        imap_uid=imap_uid,
        skip_before_reply=bool(skip_information),
        skip_reason=skip_information.get("skip_reason"),
        skip_detail=skip_information.get("skip_detail"),
        blocked_sender_domain=skip_information.get("blocked_sender_domain"),
        blocked_sender_keyword=skip_information.get("blocked_sender_keyword"),
    )
