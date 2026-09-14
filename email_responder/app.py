"""Run the Wieland Collective automatic email responder without n8n.

The program follows the same steps as the original n8n workflow:

1. Read unread Gmail messages over IMAP.
2. Ignore messages from the mailbox itself and known blocked senders.
3. Claim each message in PostgreSQL so it can never be answered twice.
4. Find the most relevant Wiki.js pages with OpenAI embeddings and pgvector.
5. Ask an OpenAI model to draft a concise reply.
6. Send the reply through Gmail SMTP and save the result in PostgreSQL.

The code is intentionally split into small, named functions so that someone who
is learning Python can follow the data from the inbox to the outgoing reply.
"""

from __future__ import annotations

import argparse
import html
import imaplib
import json
import logging
import os
import re
import smtplib
import ssl
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import psycopg
from dotenv import load_dotenv
from openai import OpenAI
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

LOGGER = logging.getLogger("email_responder")

DEFAULT_BLOCKED_DOMAINS = (
    "freelancer.nl",
    "freelancer.com",
    "makro.nl",
    "makromarket.nl",
    "makro.market",
    "makro-market.nl",
)

DEFAULT_BLOCKED_KEYWORDS = (
    "freelancer.nl",
    "makro market",
    "makromarket",
    "makro-market",
)

PAGE_QUERY = """
query PageContent($id: Int!) {
  pages {
    single(id: $id) {
      id
      path
      title
      description
      content
      render
      locale
      editor
      createdAt
      updatedAt
    }
  }
}
""".strip()


# Example: values = split_csv("one, two")
def split_csv(value: str) -> tuple[str, ...]:
    """Turn a comma-separated environment value into clean lowercase items."""

    return tuple(item.strip().lower() for item in value.split(",") if item.strip())


# Example: enabled = parse_boolean("yes")
def parse_boolean(value: str) -> bool:
    """Return ``True`` for common true-like environment values."""

    return value.strip().lower() in {"1", "true", "yes", "on"}


# Example: settings = Settings.from_environment()
@dataclass(frozen=True)
class Settings:
    """Configuration loaded from environment variables or a local ``.env`` file."""

    account_email: str
    gmail_app_password: str
    openai_api_key: str
    wikijs_api_token: str
    database_url: str
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_mailbox: str = "INBOX"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    wikijs_graphql_url: str = "http://127.0.0.1:3000/graphql"
    response_model: str = "gpt-5.4"
    embedding_model: str = "text-embedding-3-small"
    poll_seconds: int = 60
    store_openai_responses: bool = False
    blocked_domains: tuple[str, ...] = DEFAULT_BLOCKED_DOMAINS
    blocked_keywords: tuple[str, ...] = DEFAULT_BLOCKED_KEYWORDS

    # Example: settings = Settings.from_environment()
    @classmethod
    def from_environment(cls) -> Settings:
        """Load settings after reading an optional, untracked ``.env`` file."""

        load_dotenv()

        postgres_user = os.getenv("POSTGRES_USER", "appuser")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "change-me-for-local-dev")
        postgres_host = os.getenv("POSTGRES_HOST", "127.0.0.1")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_database = os.getenv("POSTGRES_DB", "freelance")
        default_database_url = (
            f"postgresql://{postgres_user}:{postgres_password}"
            f"@{postgres_host}:{postgres_port}/{postgres_database}"
        )

        return cls(
            account_email=os.getenv(
                "EMAIL_RESPONDER_ACCOUNT", "hello.wieland.collective@gmail.com"
            ).lower(),
            gmail_app_password=os.getenv("GMAIL_APP_PASSWORD", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            wikijs_api_token=os.getenv("WIKIJS_API_TOKEN", ""),
            database_url=os.getenv("DATABASE_URL", default_database_url),
            imap_host=os.getenv("EMAIL_RESPONDER_IMAP_HOST", "imap.gmail.com"),
            imap_port=int(os.getenv("EMAIL_RESPONDER_IMAP_PORT", "993")),
            imap_mailbox=os.getenv("EMAIL_RESPONDER_IMAP_MAILBOX", "INBOX"),
            smtp_host=os.getenv("EMAIL_RESPONDER_SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("EMAIL_RESPONDER_SMTP_PORT", "465")),
            wikijs_graphql_url=os.getenv(
                "WIKIJS_GRAPHQL_URL", "http://127.0.0.1:3000/graphql"
            ),
            response_model=os.getenv("OPENAI_RESPONSE_MODEL", "gpt-5.4"),
            embedding_model=os.getenv(
                "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
            ),
            poll_seconds=max(5, int(os.getenv("EMAIL_RESPONDER_POLL_SECONDS", "60"))),
            store_openai_responses=parse_boolean(
                os.getenv("OPENAI_STORE_RESPONSES", "false")
            ),
            blocked_domains=split_csv(
                os.getenv(
                    "EMAIL_RESPONDER_BLOCKED_DOMAINS",
                    ",".join(DEFAULT_BLOCKED_DOMAINS),
                )
            ),
            blocked_keywords=split_csv(
                os.getenv(
                    "EMAIL_RESPONDER_BLOCKED_KEYWORDS",
                    ",".join(DEFAULT_BLOCKED_KEYWORDS),
                )
            ),
        )

    # Example: settings.validate(require_gmail=False)
    def validate(
        self,
        require_gmail: bool = True,
        require_openai: bool = True,
        require_wikijs: bool = True,
    ) -> None:
        """Raise a helpful error when a required secret is missing."""

        missing: list[str] = []
        if require_gmail and not self.gmail_app_password:
            missing.append("GMAIL_APP_PASSWORD")
        if require_openai and not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if require_wikijs and not self.wikijs_api_token:
            missing.append("WIKIJS_API_TOKEN")

        if missing:
            names = ", ".join(missing)
            raise ValueError(f"Missing required environment variable(s): {names}")


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


# Example: clean = strip_html("<p>Hello</p>")
def strip_html(value: str) -> str:
    """Remove scripts, styles, and HTML tags while keeping readable spacing."""

    without_scripts = re.sub(
        r"<script[\s\S]*?</script>", " ", value, flags=re.IGNORECASE
    )
    without_styles = re.sub(
        r"<style[\s\S]*?</style>", " ", without_scripts, flags=re.IGNORECASE
    )
    with_line_breaks = re.sub(r"<br\s*/?>", "\n", without_styles, flags=re.IGNORECASE)
    with_paragraphs = re.sub(r"</p>", "\n\n", with_line_breaks, flags=re.IGNORECASE)
    without_tags = re.sub(r"<[^>]+>", " ", with_paragraphs)
    # html.unescape turns &nbsp; into a non-breaking space. The old workflow
    # used a normal space, which behaves better during whitespace cleanup.
    return html.unescape(without_tags).replace("\u00a0", " ")


# Example: clean = normalize_whitespace("Hello   world")
def normalize_whitespace(value: str) -> str:
    """Normalize spaces and blank lines without flattening paragraphs."""

    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[\t ]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


# Example: clean = normalize_text("<p>Hello</p>")
def normalize_text(value: str) -> str:
    """Convert possible HTML into normalized plain text."""

    return normalize_whitespace(strip_html(value))


# Example: chunks = chunk_text("A long message", max_length=1200, overlap=180)
def chunk_text(text: str, max_length: int = 1200, overlap: int = 180) -> list[str]:
    """Split text into overlapping chunks like the original n8n workflow."""

    if not text:
        return []
    if max_length <= 0:
        raise ValueError("max_length must be greater than zero")
    if overlap < 0 or overlap >= max_length:
        raise ValueError("overlap must be at least zero and smaller than max_length")

    blocks = [
        block.strip()
        for block in re.split(r"\n(?=#{1,6}\s)|\n\n+", text)
        if block.strip()
    ]
    chunks: list[str] = []
    current = ""

    for block in blocks:
        if len(block) > max_length:
            if current:
                chunks.append(current.strip())
                current = ""

            step = max_length - overlap
            for start in range(0, len(block), step):
                piece = block[start : start + max_length].strip()
                if piece:
                    chunks.append(piece)
            continue

        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) > max_length:
            if current:
                chunks.append(current.strip())
            current = block
        else:
            current = candidate

    if current:
        chunks.append(current.strip())

    return chunks


# Example: key = workflow_hash("sender@example.com")
def workflow_hash(value: str) -> str:
    """Reproduce the n8n workflow's 64-bit-looking fallback message hash."""

    # JavaScript charCodeAt reads UTF-16 code units, so Python must do the same.
    encoded = value.encode("utf-16-le", errors="surrogatepass")
    character_codes = [
        int.from_bytes(encoded[index : index + 2], "little")
        for index in range(0, len(encoded), 2)
    ]

    mask = 0xFFFFFFFF
    h1 = 0xDEADBEEF
    h2 = 0x41C6CE57

    for character_code in character_codes:
        h1 = ((h1 ^ character_code) * 2654435761) & mask
        h2 = ((h2 ^ character_code) * 1597334677) & mask

    h1 = (
        (((h1 ^ (h1 >> 16)) * 2246822507) & mask)
        ^ (((h2 ^ (h2 >> 13)) * 3266489909) & mask)
    ) & mask
    h2 = (
        (((h2 ^ (h2 >> 16)) * 2246822507) & mask)
        ^ (((h1 ^ (h1 >> 13)) * 3266489909) & mask)
    ) & mask
    return f"{h2:08x}{h1:08x}"


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
        if part.is_multipart():
            continue
        if part.get_content_disposition() == "attachment":
            continue

        content_type = part.get_content_type()
        if content_type == "text/plain":
            plain_parts.append(decode_message_part(part))
        elif content_type == "text/html":
            html_parts.append(decode_message_part(part))

    return "\n".join(plain_parts), "\n".join(html_parts)


# Example: reason = blocked_sender_reason("news@example.com", "News", settings)
def blocked_sender_reason(
    sender_email: str, sender_raw: str, settings: Settings
) -> dict[str, str]:
    """Explain why a sender matches the configured domain or name blocklist."""

    sender_domain = sender_email.rsplit("@", 1)[-1]
    for blocked_domain in settings.blocked_domains:
        if sender_domain == blocked_domain or sender_domain.endswith(
            f".{blocked_domain}"
        ):
            return {
                "skip_reason": "blocked_sender",
                "skip_detail": f"sender domain matches {blocked_domain}",
                "blocked_sender_domain": blocked_domain,
            }

    lowered_sender = normalize_whitespace(sender_raw).lower()
    for blocked_keyword in settings.blocked_keywords:
        if blocked_keyword in lowered_sender:
            return {
                "skip_reason": "blocked_sender",
                "skip_detail": f"sender name matches {blocked_keyword}",
                "blocked_sender_keyword": blocked_keyword,
            }

    return {}


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


# Example: payload = make_manual_test_email(settings)
def make_manual_test_email(settings: Settings) -> IncomingEmail:
    """Create the safe Gmail plus-address test used by the old manual trigger."""

    now = datetime.now(UTC)
    run_id = now.strftime("%Y%m%d%H%M%S%f")
    sender = settings.account_email.replace("@", "+manual-test@", 1)
    subject = f"Manual responder Python test {now.isoformat()}"
    body = "\n".join(
        [
            "Hello Wieland Collective,",
            "",
            "This is a manual test email for the automatic responder program.",
            "Please answer as if I am asking what services you offer "
            "and how to start a project.",
            "",
            "Thanks!",
            "Manual Test",
        ]
    )
    received_at = now.isoformat()
    sender_raw = f"Manual Test <{sender}>"

    return IncomingEmail(
        mailbox=settings.account_email,
        account_email=settings.account_email,
        sender_email=sender,
        sender_raw=sender_raw,
        to_raw=settings.account_email,
        cc_raw="",
        received_at=received_at,
        message_id=f"<manual-test-{run_id}@python.local>",
        message_key=f"<manual-test-{run_id}@python.local>",
        original_subject=subject,
        reply_subject=f"Re: {subject}",
        email_text=body,
        full_email="\n".join(
            [
                f"From: {sender_raw}",
                f"To: {settings.account_email}",
                f"Date: {received_at}",
                f"Subject: {subject}",
                "",
                body,
            ]
        ),
        imap_uid=None,
    )


# Example: database = Database(settings.database_url)
class Database:
    """Store message claims and search the existing pgvector knowledge base."""

    # Example: database = Database("postgresql://user:pass@localhost/database")
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    # Example: result = database.claim_email(payload)
    def claim_email(self, payload: IncomingEmail) -> ClaimResult:
        """Atomically claim, skip, or recognize an already-seen email."""

        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO public.email_responder_state
                      (mailbox, respond_after, top_k)
                    VALUES (%s, now(), 5)
                    ON CONFLICT (mailbox) DO NOTHING
                    """,
                    (payload.mailbox,),
                )
                cursor.execute(
                    """
                    SELECT respond_after, top_k
                    FROM public.email_responder_state
                    WHERE mailbox = %s
                    """,
                    (payload.mailbox,),
                )
                state = cursor.fetchone()
                if state is None:
                    raise RuntimeError("Email responder state could not be loaded.")

                received_at = datetime.fromisoformat(payload.received_at)
                if received_at < state["respond_after"]:
                    new_status = "skipped_old"
                elif payload.skip_reason:
                    new_status = "skipped_blocked"
                else:
                    new_status = "processing"

                cursor.execute(
                    """
                    INSERT INTO public.email_responder_messages (
                      mailbox, message_key, message_id, imap_uid, sender_email,
                      sender_raw, subject, received_at, status, email_payload,
                      claimed_at, updated_at
                    )
                    VALUES (
                      %s, %s, NULLIF(%s, ''), %s, %s, %s, %s, %s, %s, %s,
                      CASE WHEN %s = 'processing' THEN now() ELSE NULL END,
                      now()
                    )
                    ON CONFLICT (mailbox, message_key) DO NOTHING
                    RETURNING id, status
                    """,
                    (
                        payload.mailbox,
                        payload.message_key,
                        payload.message_id,
                        payload.imap_uid,
                        payload.sender_email,
                        payload.sender_raw,
                        payload.original_subject,
                        received_at,
                        new_status,
                        Jsonb(payload.to_dict()),
                        new_status,
                    ),
                )
                inserted = cursor.fetchone()
                if inserted is not None:
                    return ClaimResult(
                        record_id=int(inserted["id"]),
                        should_reply=new_status == "processing",
                        status=str(inserted["status"]),
                        top_k=int(state["top_k"]),
                    )

                cursor.execute(
                    """
                    SELECT id, status
                    FROM public.email_responder_messages
                    WHERE mailbox = %s AND message_key = %s
                    """,
                    (payload.mailbox, payload.message_key),
                )
                existing = cursor.fetchone()
                if existing is None:
                    raise RuntimeError(
                        "Email claim disappeared before it could be read."
                    )

                return ClaimResult(
                    record_id=int(existing["id"]),
                    should_reply=False,
                    status=str(existing["status"]),
                    top_k=int(state["top_k"]),
                )

    # Example: pages = database.rank_pages(embeddings, top_k=5)
    def rank_pages(
        self, embeddings: Sequence[Sequence[float]], top_k: int
    ) -> list[RankedPage]:
        """Find the nearest knowledge-base page across every email chunk."""

        best_pages: dict[str, RankedPage] = {}
        query = """
            WITH email_embedding AS (
              SELECT %s::vector AS embedding
            ), ranked_chunks AS (
              SELECT
                kb.page_id,
                kb.path,
                kb.title,
                kb.wiki_url,
                kb.chunk_index,
                kb.chunk_text,
                kb.embedding <=> email_embedding.embedding AS distance
              FROM public.kb_chunks AS kb
              CROSS JOIN email_embedding
            )
            SELECT DISTINCT ON (page_id)
              page_id,
              path,
              title,
              wiki_url,
              chunk_index,
              chunk_text,
              distance
            FROM ranked_chunks
            ORDER BY page_id, distance ASC
        """

        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                for email_chunk_index, embedding in enumerate(embeddings):
                    vector_text = (
                        "[" + ",".join(str(value) for value in embedding) + "]"
                    )
                    cursor.execute(query, (vector_text,))
                    for row in cursor.fetchall():
                        page_id = str(row["page_id"])
                        distance = float(row["distance"])
                        current = best_pages.get(page_id)
                        if current is None or distance < current.best_distance:
                            best_pages[page_id] = RankedPage(
                                page_id=page_id,
                                path=str(row["path"] or ""),
                                title=str(row["title"] or row["path"] or page_id),
                                wiki_url=row["wiki_url"],
                                best_distance=distance,
                                matched_email_chunk_index=email_chunk_index,
                                matched_chunk_index=int(row["chunk_index"]),
                                matched_chunk_text=str(row["chunk_text"] or ""),
                            )

        ranked = sorted(best_pages.values(), key=lambda page: page.best_distance)
        if not ranked:
            raise RuntimeError(
                "No knowledge-base rows were found. "
                "Run the Wiki.js embedding index first."
            )

        selected = ranked[: min(top_k, len(ranked))]
        for rank, page in enumerate(selected, start=1):
            page.rank = rank
        return selected

    # Example: database.mark_replied(payload, pages, body, result)
    def mark_replied(
        self,
        payload: IncomingEmail,
        pages: Sequence[RankedPage],
        reply_body: str,
        send_result: dict[str, Any],
    ) -> None:
        """Record a successfully sent reply."""

        self._mark_outcome(
            payload=payload,
            status="replied",
            pages=pages,
            reply_body=reply_body,
            send_result=send_result,
            error_message=None,
        )

    # Example: database.mark_failed(payload, "SMTP timed out")
    def mark_failed(
        self,
        payload: IncomingEmail,
        error_message: str,
        pages: Sequence[RankedPage] = (),
        reply_body: str = "",
    ) -> None:
        """Record a failed draft or send attempt for later inspection."""

        self._mark_outcome(
            payload=payload,
            status="failed",
            pages=pages,
            reply_body=reply_body,
            send_result={"error": error_message},
            error_message=error_message,
        )

    # Example: database._mark_outcome(payload, "failed", [], "", {}, "error")
    def _mark_outcome(
        self,
        payload: IncomingEmail,
        status: str,
        pages: Sequence[RankedPage],
        reply_body: str,
        send_result: dict[str, Any],
        error_message: str | None,
    ) -> None:
        """Write the common fields shared by successful and failed outcomes."""

        page_data = [page.to_dict() for page in pages]
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE public.email_responder_messages
                    SET
                      status = %s,
                      matched_pages = %s,
                      reply_subject = %s,
                      reply_body = %s,
                      send_result = %s,
                      replied_at = CASE
                        WHEN %s = 'replied' THEN now()
                        ELSE replied_at
                      END,
                      last_error = %s,
                      updated_at = now()
                    WHERE mailbox = %s AND message_key = %s
                    """,
                    (
                        status,
                        Jsonb(page_data),
                        payload.reply_subject,
                        reply_body,
                        Jsonb(send_result),
                        status,
                        error_message,
                        payload.mailbox,
                        payload.message_key,
                    ),
                )

    # Example: database.reset_baseline("hello@example.com")
    def reset_baseline(self, mailbox: str) -> None:
        """Set the old-mail cutoff to now before enabling the responder."""

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO public.email_responder_state
                      (mailbox, respond_after, top_k, updated_at)
                    VALUES (%s, now(), 5, now())
                    ON CONFLICT (mailbox) DO UPDATE
                    SET respond_after = now(), updated_at = now()
                    """,
                    (mailbox,),
                )


# Example: client = WikiJsClient(settings)
class WikiJsClient:
    """Fetch full Wiki.js pages through its GraphQL API."""

    # Example: client = WikiJsClient(settings)
    def __init__(self, settings: Settings) -> None:
        self.graphql_url = settings.wikijs_graphql_url
        token = settings.wikijs_api_token.strip()
        self.authorization = (
            token if token.lower().startswith("bearer ") else f"Bearer {token}"
        )

    # Example: page = client.fetch_page(ranked_page)
    def fetch_page(self, ranked_page: RankedPage) -> RankedPage:
        """Attach current Wiki.js content to one ranked page."""

        body = json.dumps(
            {"query": PAGE_QUERY, "variables": {"id": int(ranked_page.page_id)}}
        ).encode("utf-8")
        request = Request(
            self.graphql_url,
            data=body,
            method="POST",
            headers={
                "Authorization": self.authorization,
                "Content-Type": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=30) as response:
                result = json.load(response)
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Wiki.js returned HTTP {error.code}: {details}"
            ) from error
        except URLError as error:
            raise RuntimeError(f"Could not reach Wiki.js: {error.reason}") from error

        if result.get("errors"):
            messages = "; ".join(
                str(item.get("message", item)) for item in result["errors"]
            )
            raise RuntimeError(f"Wiki.js GraphQL error: {messages}")

        page_data = result.get("data", {}).get("pages", {}).get("single")
        if not page_data:
            raise RuntimeError(
                f"Wiki.js returned no page content for page {ranked_page.page_id}."
            )

        ranked_page.title = str(
            page_data.get("title") or ranked_page.title or ranked_page.page_id
        )
        ranked_page.path = str(page_data.get("path") or ranked_page.path)
        ranked_page.content = normalize_text(
            str(page_data.get("content") or page_data.get("render") or "")
        )
        return ranked_page


# Example: prompt = build_reply_prompt(payload, pages)
def build_reply_prompt(payload: IncomingEmail, pages: Sequence[RankedPage]) -> str:
    """Build the same grounded reply request used by the n8n workflow."""

    context_sections: list[str] = []
    for page in sorted(pages, key=lambda item: item.rank):
        lines = [
            f"## {page.rank}. {page.title}",
            f"Path: {page.path}",
        ]
        if page.wiki_url:
            lines.append(f"URL: {page.wiki_url}")
        lines.extend(
            [
                f"Best embedding distance: {page.best_distance}",
                f"Matched email chunk: {page.matched_email_chunk_index}",
                f"Matched KB chunk: {page.matched_chunk_index}",
                "",
                page.content,
            ]
        )
        context_sections.append("\n".join(lines))

    knowledge_base_context = "\n\n---\n\n".join(context_sections)
    return "\n".join(
        [
            "You are replying on behalf of Wieland Collective from "
            f"{payload.account_email}.",
            "",
            "Write a helpful email reply to the sender. Use the Wiki.js "
            "knowledge-base pages below as the factual context for the reply. "
            "Do not invent details that are not supported by the context or the "
            "incoming email. If the context does not answer a specific question, "
            "say that we will follow up. Keep the tone warm, concise, and "
            "professional. Match the incoming email language when practical. "
            "Return only the email body; do not include a subject line, markdown "
            "code fence, or analysis.",
            "",
            f"# Retrieved Wiki.js Context ({len(pages)} distinct pages)",
            knowledge_base_context,
            "",
            "# Incoming Email",
            payload.full_email,
            "",
            "# Reply Body",
        ]
    )


# Example: ai = OpenAIClient(settings)
class OpenAIClient:
    """Create embeddings and draft the final email body with OpenAI."""

    # Example: ai = OpenAIClient(settings)
    def __init__(self, settings: Settings) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.embedding_model = settings.embedding_model
        self.response_model = settings.response_model
        self.store_responses = settings.store_openai_responses

    # Example: vectors = ai.create_embeddings(["first chunk", "second chunk"])
    def create_embeddings(self, chunks: Sequence[str]) -> list[list[float]]:
        """Embed all non-empty email chunks in one API request."""

        if not chunks:
            raise ValueError("At least one email chunk is required for embeddings.")

        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=list(chunks),
        )
        ordered_items = sorted(response.data, key=lambda item: item.index)
        return [list(item.embedding) for item in ordered_items]

    # Example: body = ai.draft_reply(prompt)
    def draft_reply(self, prompt: str) -> str:
        """Generate a reply body with the configured Responses API model."""

        response = self.client.responses.create(
            model=self.response_model,
            input=prompt,
            store=self.store_responses,
        )
        reply_body = str(response.output_text or "").strip()
        if not reply_body:
            raise RuntimeError("OpenAI returned an empty email reply.")
        return reply_body


# Example: mail = GmailClient(settings)
class GmailClient:
    """Read unread Gmail messages with IMAP and send replies with SMTP."""

    # Example: mail = GmailClient(settings)
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # Example: messages = mail.read_unseen()
    def read_unseen(self) -> list[tuple[int, Message]]:
        """Fetch unread inbox messages without marking them read yet."""

        messages: list[tuple[int, Message]] = []
        with imaplib.IMAP4_SSL(
            self.settings.imap_host, self.settings.imap_port
        ) as mailbox:
            mailbox.login(self.settings.account_email, self.settings.gmail_app_password)
            status, _ = mailbox.select(self.settings.imap_mailbox)
            if status != "OK":
                raise RuntimeError(
                    f"Could not select IMAP mailbox {self.settings.imap_mailbox}."
                )

            status, search_data = mailbox.uid("search", None, "UNSEEN")
            if status != "OK":
                raise RuntimeError("Gmail IMAP search for unread messages failed.")

            uid_values = (
                search_data[0].split() if search_data and search_data[0] else []
            )
            for uid_bytes in uid_values:
                uid = int(uid_bytes)
                status, fetched = mailbox.uid("fetch", uid_bytes, "(BODY.PEEK[])")
                if status != "OK":
                    LOGGER.error("Could not fetch IMAP UID %s.", uid)
                    continue

                raw_message = next(
                    (
                        item[1]
                        for item in fetched
                        if isinstance(item, tuple) and isinstance(item[1], bytes)
                    ),
                    None,
                )
                if raw_message is None:
                    LOGGER.error("IMAP UID %s did not contain a message body.", uid)
                    continue

                parsed = BytesParser(policy=policy.default).parsebytes(raw_message)
                messages.append((uid, parsed))

        return messages

    # Example: mail.mark_seen(123)
    def mark_seen(self, uid: int) -> None:
        """Mark one handled Gmail message as read."""

        with imaplib.IMAP4_SSL(
            self.settings.imap_host, self.settings.imap_port
        ) as mailbox:
            mailbox.login(self.settings.account_email, self.settings.gmail_app_password)
            mailbox.select(self.settings.imap_mailbox)
            status, _ = mailbox.uid("store", str(uid), "+FLAGS", "(\\Seen)")
            if status != "OK":
                raise RuntimeError(f"Could not mark IMAP UID {uid} as read.")

    # Example: result = mail.send_reply(payload, "Thank you for your email.")
    def send_reply(self, payload: IncomingEmail, reply_body: str) -> dict[str, Any]:
        """Send a plain-text response through Gmail SMTP."""

        message = EmailMessage()
        message["From"] = payload.account_email
        message["To"] = payload.sender_email
        message["Reply-To"] = payload.account_email
        message["Subject"] = payload.reply_subject
        if payload.message_id:
            message["In-Reply-To"] = payload.message_id
            message["References"] = payload.message_id
        message.set_content(reply_body)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            self.settings.smtp_host,
            self.settings.smtp_port,
            context=context,
            timeout=30,
        ) as smtp:
            smtp.login(self.settings.account_email, self.settings.gmail_app_password)
            refused = smtp.send_message(message)

        if refused:
            raise RuntimeError(f"SMTP refused recipients: {refused}")
        return {
            "accepted": True,
            "to": payload.sender_email,
            "subject": payload.reply_subject,
        }


# Example: responder = EmailResponder(settings)
class EmailResponder:
    """Coordinate the database, Wiki.js, OpenAI, IMAP, and SMTP steps."""

    # Example: responder = EmailResponder(settings)
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.database = Database(settings.database_url)
        self.wiki = WikiJsClient(settings)
        self.openai = OpenAIClient(settings)
        self.gmail = GmailClient(settings)

    # Example: body, pages = responder.create_draft(payload, top_k=5)
    def create_draft(
        self, payload: IncomingEmail, top_k: int
    ) -> tuple[str, list[RankedPage]]:
        """Retrieve relevant knowledge and create one grounded reply draft."""

        chunks = chunk_text(normalize_text(payload.email_text))
        if not chunks:
            raise ValueError("Email text produced zero chunks after normalization.")

        embeddings = self.openai.create_embeddings(chunks)
        ranked_pages = self.database.rank_pages(embeddings, top_k)
        pages_with_content = [self.wiki.fetch_page(page) for page in ranked_pages]
        prompt = build_reply_prompt(payload, pages_with_content)
        reply_body = self.openai.draft_reply(prompt)
        return reply_body, pages_with_content

    # Example: status = responder.process_email(payload)
    def process_email(self, payload: IncomingEmail) -> str:
        """Claim one normalized email, draft its reply, send it, and save the result."""

        claim = self.database.claim_email(payload)
        if not claim.should_reply:
            LOGGER.info(
                "Skipped %s from %s because its status is %s.",
                payload.message_key,
                payload.sender_email,
                claim.status,
            )
            return claim.status

        pages: list[RankedPage] = []
        reply_body = ""
        try:
            reply_body, pages = self.create_draft(payload, claim.top_k)
            send_result = self.gmail.send_reply(payload, reply_body)
            self.database.mark_replied(payload, pages, reply_body, send_result)
        except Exception as error:
            error_message = f"{type(error).__name__}: {error}"
            LOGGER.exception("Reply failed for %s.", payload.message_key)
            try:
                self.database.mark_failed(
                    payload, error_message, pages=pages, reply_body=reply_body
                )
            except Exception:
                LOGGER.exception(
                    "Could not store the failure for %s.", payload.message_key
                )
            return "failed"

        LOGGER.info(
            "Replied to %s about %s.",
            payload.sender_email,
            payload.original_subject,
        )
        return "replied"

    # Example: draft = responder.preview_email(payload, top_k=5)
    def preview_email(self, payload: IncomingEmail, top_k: int = 5) -> str:
        """Create and return a draft without claiming or sending the email."""

        reply_body, pages = self.create_draft(payload, top_k)
        LOGGER.info("Draft used %s Wiki.js page(s).", len(pages))
        return reply_body

    # Example: handled = responder.run_once()
    def run_once(self) -> int:
        """Process every unread message currently visible in the Gmail inbox."""

        unread_messages = self.gmail.read_unseen()
        LOGGER.info("Found %s unread message(s).", len(unread_messages))

        for uid, message in unread_messages:
            try:
                payload = normalize_message(message, uid, self.settings)
                if payload is None:
                    LOGGER.info(
                        "Ignored a message sent by the responder mailbox itself."
                    )
                else:
                    self.process_email(payload)
            except Exception:
                LOGGER.exception("Could not process IMAP UID %s.", uid)
            finally:
                try:
                    self.gmail.mark_seen(uid)
                except Exception:
                    LOGGER.exception("Could not mark IMAP UID %s as read.", uid)

        return len(unread_messages)

    # Example: responder.run_forever()
    def run_forever(self) -> None:
        """Poll Gmail forever, recovering from temporary connection failures."""

        LOGGER.info(
            "Email responder started for %s; polling every %s seconds.",
            self.settings.account_email,
            self.settings.poll_seconds,
        )
        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                raise
            except Exception:
                LOGGER.exception("Inbox poll failed; the responder will retry.")
            time.sleep(self.settings.poll_seconds)


# Example: parser = build_argument_parser()
def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line options for normal runs and safe testing."""

    parser = argparse.ArgumentParser(
        description="Run the Wieland Collective email responder without n8n."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Check the inbox once and then exit instead of polling forever.",
    )
    parser.add_argument(
        "--manual-test",
        action="store_true",
        help="Create the same synthetic test email as the old manual workflow.",
    )
    parser.add_argument(
        "--draft-only",
        action="store_true",
        help="With --manual-test, print a draft without claiming or sending it.",
    )
    parser.add_argument(
        "--reset-baseline",
        action="store_true",
        help="Set the old-email cutoff to now, then exit.",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default=os.getenv("EMAIL_RESPONDER_LOG_LEVEL", "INFO").upper(),
        help="Choose how much information the program prints.",
    )
    return parser


# Example: configure_logging("INFO")
def configure_logging(level: str) -> None:
    """Configure readable timestamped console logs."""

    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


# Example: main(["--once"])
def main(arguments: Sequence[str] | None = None) -> None:
    """Validate configuration and run the selected command."""

    parser = build_argument_parser()
    args = parser.parse_args(arguments)
    configure_logging(args.log_level)

    if args.draft_only and not args.manual_test:
        parser.error("--draft-only must be used together with --manual-test")

    settings = Settings.from_environment()

    if args.reset_baseline:
        settings.validate(
            require_gmail=False,
            require_openai=False,
            require_wikijs=False,
        )
        Database(settings.database_url).reset_baseline(settings.account_email)
        LOGGER.info("Old-email cutoff reset for %s.", settings.account_email)
        return

    settings.validate(require_gmail=not args.draft_only)
    responder = EmailResponder(settings)

    if args.manual_test:
        payload = make_manual_test_email(settings)
        if args.draft_only:
            print(responder.preview_email(payload))
        else:
            status = responder.process_email(payload)
            LOGGER.info("Manual test finished with status %s.", status)
        return

    if args.once:
        responder.run_once()
        return

    try:
        responder.run_forever()
    except KeyboardInterrupt:
        LOGGER.info("Email responder stopped.")


if __name__ == "__main__":
    main()
