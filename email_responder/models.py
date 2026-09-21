"""Data objects shared by the responder's independent components."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


# Example: payload = IncomingEmail(...)
@dataclass
class IncomingEmail:
    """Normalized fields used throughout the responder."""

    mailbox: str
    account_email: str
    sender_email: str
    sender_raw: str
    to_raw: str
    cc_raw: str
    received_at: str
    message_id: str
    message_key: str
    original_subject: str
    reply_subject: str
    email_text: str
    full_email: str
    imap_uid: int | None
    gmail_id: str = ""
    gmail_thread_id: str = ""
    skip_before_reply: bool = False
    skip_reason: str | None = None
    skip_detail: str | None = None
    blocked_sender_domain: str | None = None
    blocked_sender_keyword: str | None = None

    # Example: data = payload.to_dict()
    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary for PostgreSQL and logging."""

        return asdict(self)


# Example: result = ClaimResult(1, True, "processing", 5)
@dataclass(frozen=True)
class ClaimResult:
    """Describe whether the current process owns an incoming message."""

    record_id: int
    should_reply: bool
    status: str
    top_k: int


# Example: page = RankedPage("12", "/services", "Services", None, 0.2, 0, 1)
@dataclass
class RankedPage:
    """A Wiki.js page selected by semantic similarity."""

    page_id: str
    path: str
    title: str
    wiki_url: str | None
    best_distance: float
    matched_email_chunk_index: int
    matched_chunk_index: int
    matched_chunk_text: str = ""
    content: str = ""
    rank: int = 0

    # Example: data = page.to_dict()
    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary for the responder history table."""

        return asdict(self)


# Example: draft = ReplyDraft("Thank you for your email.", pages)
@dataclass
class ReplyDraft:
    """A reply body and the knowledge-base pages used to write it."""

    body: str
    pages: list[RankedPage]
