"""Repeat the single-email workflow for an inbox, once or on a timer.

Each message is handled independently. A malformed message or a temporary
failure must not prevent the next message from being handled.
"""

import logging
import time
from email.message import Message

from .config import Settings
from .mail.normalize import normalize_message
from .responder import EmailResponder
from .services.gmail import GmailClient

LOGGER = logging.getLogger("email_responder")


# Example: inbox = InboxRunner(settings, gmail, responder)
class InboxRunner:
    """Own inbox polling, leaving the reply workflow focused on one email."""

    # Example: inbox = InboxRunner(settings, gmail, responder)
    def __init__(
        self, settings: Settings, gmail: GmailClient, responder: EmailResponder
    ) -> None:
        """Remember the mailbox, reply workflow, and polling interval."""

        self.settings = settings
        self.gmail = gmail
        self.responder = responder

    # Example: handled = inbox.run_once()
    def run_once(self) -> int:
        """Handle each unread message and return how many were fetched."""

        messages = self.gmail.read_unseen()
        LOGGER.info("Found %s unread message(s).", len(messages))
        for uid, message in messages:
            self.handle_message(uid, message)
        return len(messages)

    # Example: inbox.run_forever()
    def run_forever(self) -> None:
        """Poll until interrupted, recovering from temporary connection failures."""

        LOGGER.info(
            "Email responder started for %s; polling every %s seconds.",
            self.settings.account_email,
            self.settings.poll_seconds,
        )
        while True:
            try:
                self.run_once()
            except Exception:
                # KeyboardInterrupt is not an Exception, so Ctrl+C still exits.
                LOGGER.exception("Inbox poll failed; the responder will retry.")
            time.sleep(self.settings.poll_seconds)

    # Example: inbox.handle_message(123, parsed_message)
    def handle_message(self, uid: int, message: Message) -> None:
        """Normalize and answer one message, then mark it read even on failure."""

        try:
            email = normalize_message(message, uid, self.settings)
            if email is None:
                LOGGER.info("Ignored a message sent by the responder mailbox itself.")
            else:
                self.responder.process_email(email)
        except Exception:
            LOGGER.exception("Could not process IMAP UID %s.", uid)
        finally:
            # Preserve the existing policy: handled failures are read too.
            # Their database record prevents automatic duplicate sends.
            try:
                self.gmail.mark_seen(uid)
            except Exception:
                LOGGER.exception("Could not mark IMAP UID %s as read.", uid)
