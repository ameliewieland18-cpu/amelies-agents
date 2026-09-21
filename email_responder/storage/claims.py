"""Atomically decide whether this process may reply to a message.

All steps use one transaction. The unique message key prevents two workers
from claiming the same email, even when they check at the same time.
"""

from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from ..models import ClaimResult, IncomingEmail
from . import queries


# Example: result = claim_email(database_url, payload)
def claim_email(database_url: str, payload: IncomingEmail) -> ClaimResult:
    """Atomically claim, skip, or recognize an already-seen email."""

    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                queries.ENSURE_STATE,
                (payload.mailbox,),
            )
            cursor.execute(
                queries.READ_STATE,
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
                queries.INSERT_CLAIM,
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
                queries.READ_CLAIM,
                (payload.mailbox, payload.message_key),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise RuntimeError("Email claim disappeared before it could be read.")

            return ClaimResult(
                record_id=int(existing["id"]),
                should_reply=False,
                status=str(existing["status"]),
                top_k=int(state["top_k"]),
            )


# Example: reset_baseline(database_url, "hello@example.com")
def reset_baseline(database_url: str, mailbox: str) -> None:
    """Set the old-mail cutoff to now before enabling the responder."""

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                queries.RESET_BASELINE,
                (mailbox,),
            )
