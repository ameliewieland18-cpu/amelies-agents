"""Low-level email dates, character sets, and multipart bodies.

The rest of the program receives plain strings from these helpers.
"""

from datetime import UTC, datetime
from email.message import Message
from email.utils import parsedate_to_datetime


# Example: when = parse_received_date("Mon, 14 Sep 2026 12:00:00 +0200")
def parse_received_date(value: str | None) -> datetime:
    """Parse an email date and always return a timezone-aware value."""

    if not value:
        return datetime.now(UTC)

    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return datetime.now(UTC)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


# Example: body = decode_message_part(message)
def decode_message_part(message: Message) -> str:
    """Decode one text email part while tolerating unusual character sets."""

    payload = message.get_payload(decode=True)
    if payload is None:
        plain_payload = message.get_payload()
        return plain_payload if isinstance(plain_payload, str) else ""

    charset = message.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


# Example: plain, html_body = extract_bodies(message)
def extract_bodies(message: Message) -> tuple[str, str]:
    """Return the first useful plain-text and HTML bodies from an email."""

    plain_parts: list[str] = []
    html_parts: list[str] = []

    parts = message.walk() if message.is_multipart() else (message,)
    for part in parts:
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue

        content_type = part.get_content_type()
        if content_type == "text/plain":
            plain_parts.append(decode_message_part(part))
        elif content_type == "text/html":
            html_parts.append(decode_message_part(part))

    return "\n".join(plain_parts), "\n".join(html_parts)
