"""Store the final reply or error in the responder history table."""

from collections.abc import Sequence
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from ..models import IncomingEmail, RankedPage
from . import queries


# Example: save_outcome(url, email, "replied", pages, body, result, None)
def save_outcome(
    database_url: str,
    payload: IncomingEmail,
    status: str,
    pages: Sequence[RankedPage],
    reply_body: str,
    send_result: dict[str, Any],
    error_message: str | None,
) -> None:
    """Write the common fields shared by successful and failed outcomes."""

    page_data = [page.to_dict() for page in pages]
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                queries.SAVE_OUTCOME,
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
