"""The database operations the workflow can ask for.

The SQL, transactions, and row unpacking live in storage/. This small adapter
keeps those details out of the reply workflow.
"""

from collections.abc import Sequence
from typing import Any

from ..models import ClaimResult, IncomingEmail, RankedPage
from ..storage import claims, history, search


# Example: database = Database("postgresql://user:pass@localhost/database")
class Database:
    """Remember the connection address and expose named database operations."""

    # Example: database = Database(settings.database_url)
    def __init__(self, database_url: str) -> None:
        """Save the address; open connections only when an operation needs one."""

        self.database_url = database_url

    # Example: claim = database.claim_email(email)
    def claim_email(self, email: IncomingEmail) -> ClaimResult:
        """Reserve a new email, or explain why it should be skipped."""

        return claims.claim_email(self.database_url, email)

    # Example: pages = database.rank_pages(embeddings, top_k=5)
    def rank_pages(
        self, embeddings: Sequence[Sequence[float]], top_k: int
    ) -> list[RankedPage]:
        """Find up to K distinct knowledge-base pages for the email."""

        return search.rank_pages(self.database_url, embeddings, top_k)

    # Example: database.mark_replied(email, pages, body, receipt)
    def mark_replied(
        self,
        email: IncomingEmail,
        pages: Sequence[RankedPage],
        reply_body: str,
        send_result: dict[str, Any],
    ) -> None:
        """Save the answer and the mail server's receipt after sending."""

        history.save_outcome(
            self.database_url, email, "replied", pages, reply_body, send_result, None
        )

    # Example: database.mark_failed(email, "SMTP timed out")
    def mark_failed(
        self,
        email: IncomingEmail,
        error_message: str,
        pages: Sequence[RankedPage] = (),
        reply_body: str = "",
    ) -> None:
        """Save the failure, including a draft if one was already created."""

        history.save_outcome(
            self.database_url,
            email,
            "failed",
            pages,
            reply_body,
            {"error": error_message},
            error_message,
        )

    # Example: database.reset_baseline("hello@example.com")
    def reset_baseline(self, mailbox: str) -> None:
        """Ignore messages dated before now on subsequent inbox checks."""

        claims.reset_baseline(self.database_url, mailbox)
