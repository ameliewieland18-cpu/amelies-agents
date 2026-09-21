"""The three mail operations the application needs.

IMAP and SMTP are Gmail's reading and sending protocols. Their details live in
imap.py and smtp.py, so callers need only these ordinary method names.
"""

from email.message import Message
from typing import Any

from ..config import Settings
from ..models import IncomingEmail
from . import imap, smtp


# Example: gmail = GmailClient(settings)
class GmailClient:
    """Read messages, mark them handled, and send replies."""

    # Example: gmail = GmailClient(settings)
    def __init__(self, settings: Settings) -> None:
        """Remember connection settings without contacting Gmail yet."""

        self.settings = settings

    # Example: messages = gmail.read_unseen()
    def read_unseen(self) -> list[tuple[int, Message]]:
        """Fetch unread messages without changing their read status."""

        return imap.read_unseen(self.settings)

    # Example: gmail.mark_seen(123)
    def mark_seen(self, uid: int) -> None:
        """Mark one handled message as read."""

        imap.mark_seen(self.settings, uid)

    # Example: receipt = gmail.send_reply(email, "Thank you!")
    def send_reply(self, email: IncomingEmail, reply_body: str) -> dict[str, Any]:
        """Send the reply and return a small delivery receipt."""

        return smtp.send_reply(self.settings, email, reply_body)
