"""Gmail's IMAP protocol: find unread mail, fetch it, and mark it read.

BODY.PEEK[] is deliberate: fetching must not mark a message read before handling.
The unusual nested IMAP response format is unpacked only in this module.
"""

import imaplib
import logging
from email import policy
from email.message import Message
from email.parser import BytesParser

from ..config import Settings

LOGGER = logging.getLogger("email_responder")


# Example: messages = read_unseen(settings)
def read_unseen(settings: Settings) -> list[tuple[int, Message]]:
    """Return each unread message together with its mailbox identifier (UID)."""

    messages = []
    with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as mailbox:
        select_mailbox(mailbox, settings)
        status, search_data = mailbox.uid("search", None, "UNSEEN")
        if status != "OK":
            raise RuntimeError("Gmail IMAP search for unread messages failed.")

        # IMAP packs the identifiers into one space-separated byte string.
        uids = search_data[0].split() if search_data and search_data[0] else []
        for uid_bytes in uids:
            message = fetch_message(mailbox, uid_bytes)
            if message is not None:
                messages.append((int(uid_bytes), message))
    return messages


# Example: mark_seen(settings, 123)
def mark_seen(settings: Settings, uid: int) -> None:
    """Set Gmail's Seen flag for one handled message."""

    with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as mailbox:
        select_mailbox(mailbox, settings)
        status, _ = mailbox.uid("store", str(uid), "+FLAGS", "(\\Seen)")
        if status != "OK":
            raise RuntimeError(f"Could not mark IMAP UID {uid} as read.")


# Example: select_mailbox(connection, settings)
def select_mailbox(mailbox: imaplib.IMAP4_SSL, settings: Settings) -> None:
    """Log in and select the configured folder before any UID operation."""

    mailbox.login(settings.account_email, settings.gmail_app_password)
    status, _ = mailbox.select(settings.imap_mailbox)
    if status != "OK":
        raise RuntimeError(f"Could not select IMAP mailbox {settings.imap_mailbox}.")


# Example: message = fetch_message(connection, b"123")
def fetch_message(mailbox: imaplib.IMAP4_SSL, uid: bytes) -> Message | None:
    """Unpack one FETCH response; leave unreadable messages for a later poll."""

    status, fetched = mailbox.uid("fetch", uid, "(BODY.PEEK[])")
    if status != "OK":
        LOGGER.error("Could not fetch IMAP UID %s.", int(uid))
        return None

    # FETCH may mix metadata bytes with (metadata, message-bytes) tuples.
    for item in fetched:
        if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], bytes):
            return BytesParser(policy=policy.default).parsebytes(item[1])

    LOGGER.error("IMAP UID %s did not contain a message body.", int(uid))
    return None
