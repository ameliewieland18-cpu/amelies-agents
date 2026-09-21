"""The main story for one email: claim it, draft a reply, send it, save the result.

Start reading here. The supplied objects are building blocks; their modules
explain how each step works when you are ready to go one level deeper.
"""

import logging

from .drafting import ReplyDrafter
from .models import IncomingEmail, ReplyDraft
from .services.database import Database
from .services.gmail import GmailClient

LOGGER = logging.getLogger("email_responder")


# Example: responder = EmailResponder(database, drafter, gmail)
class EmailResponder:
    """Handle one email with duplicate protection and recorded outcomes."""

    # Example: responder = EmailResponder(database, drafter, gmail)
    def __init__(
        self, database: Database, drafter: ReplyDrafter, gmail: GmailClient
    ) -> None:
        """Receive ready-to-use building blocks; connections are assembled elsewhere."""

        self.database = database
        self.drafter = drafter
        self.gmail = gmail

    # Example: status = responder.process_email(email)
    def process_email(self, email: IncomingEmail) -> str:
        """Only the process that claims a new, eligible email may send its reply."""

        claim = self.database.claim_email(email)
        if not claim.should_reply:
            LOGGER.info("Skipped %s: %s.", email.message_key, claim.status)
            return claim.status

        draft = ReplyDraft(body="", pages=[])
        try:
            draft = self.drafter.create_draft(email, claim.top_k)
            receipt = self.gmail.send_reply(email, draft.body)
            self.database.mark_replied(email, draft.pages, draft.body, receipt)
        except Exception as error:
            self.record_failure(email, draft, error)
            return "failed"

        LOGGER.info(
            "Replied to %s about %s.", email.sender_email, email.original_subject
        )
        return "replied"

    # Example: body = responder.preview_email(email)
    def preview_email(self, email: IncomingEmail, top_k: int = 5) -> str:
        """Create a draft without claiming an email or sending a reply."""

        draft = self.drafter.create_draft(email, top_k)
        LOGGER.info("Draft used %s Wiki.js page(s).", len(draft.pages))
        return draft.body

    # Example: responder.record_failure(email, draft, RuntimeError("Send failed"))
    def record_failure(
        self, email: IncomingEmail, draft: ReplyDraft, error: Exception
    ) -> None:
        """Keep the original failure visible even if saving its history also fails."""

        LOGGER.exception("Reply failed for %s.", email.message_key)
        error_message = f"{type(error).__name__}: {error}"
        try:
            self.database.mark_failed(
                email, error_message, pages=draft.pages, reply_body=draft.body
            )
        except Exception:
            LOGGER.exception("Could not store the failure for %s.", email.message_key)
