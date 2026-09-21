"""Database boundary checks using a fake cursor, without a live database."""

import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from email_responder.services.database import Database
from email_responder.storage import claims, queries, search
from tests.support import make_email, make_page


# Example: cursor, connection = make_cursor()
def make_cursor():
    """Provide the context-manager shape used by psycopg connections."""

    connection = MagicMock()
    cursor = (
        connection.__enter__.return_value.cursor.return_value.__enter__.return_value
    )
    return cursor, connection


# Example: python -m unittest tests.test_storage
class ClaimTests(unittest.TestCase):
    """Check cutoff precedence, conflict handling, and parameterized payloads."""

    # Example: self.test_claim_status_and_duplicate_ownership()
    def test_claim_status_and_duplicate_ownership(self):
        """Only a newly inserted processing record authorizes a reply."""

        cases = [
            (False, False, "processing"),
            (False, True, "skipped_blocked"),
            (True, False, "skipped_old"),
            (True, True, "skipped_old"),
        ]
        for old, blocked, status in cases:
            for duplicate in (False, True):
                with self.subTest(old=old, blocked=blocked, duplicate=duplicate):
                    email = make_email()
                    email.skip_reason = "blocked_sender" if blocked else None
                    cutoff = datetime(2026, 9, 15 if old else 13, tzinfo=UTC)
                    cursor, connection = make_cursor()
                    record = {"id": 7, "status": status}
                    cursor.fetchone.side_effect = [
                        {"respond_after": cutoff, "top_k": 3},
                        None if duplicate else record,
                        record,
                    ]
                    with patch(
                        "email_responder.storage.claims.psycopg.connect",
                        return_value=connection,
                    ) as connect:
                        result = claims.claim_email("postgresql://unused", email)
                    connect.assert_called_once()
                    self.assertEqual(
                        result.should_reply, status == "processing" and not duplicate
                    )
                    self.assertEqual((result.status, result.top_k), (status, 3))
                    insert_call = cursor.execute.call_args_list[2]
                    self.assertEqual(insert_call.args[0], queries.INSERT_CLAIM)
                    self.assertEqual(insert_call.args[1][8], status)
                    self.assertEqual(insert_call.args[1][9].obj, email.to_dict())

    # Example: self.test_missing_state_and_disappeared_claim_fail_closed()
    def test_missing_state_and_disappeared_claim_fail_closed(self):
        """Missing database rows raise instead of granting permission to send."""

        state = {"respond_after": datetime(2026, 9, 1, tzinfo=UTC), "top_k": 5}
        for rows in ([None], [state, None, None]):
            with self.subTest(rows=rows):
                cursor, connection = make_cursor()
                cursor.fetchone.side_effect = rows
                with patch(
                    "email_responder.storage.claims.psycopg.connect",
                    return_value=connection,
                ):
                    with self.assertRaises(RuntimeError):
                        claims.claim_email("postgresql://unused", make_email())


# Example: python -m unittest tests.test_storage.SearchTests
class SearchTests(unittest.TestCase):
    """Multiple chunks must still return K distinct pages with their best match."""

    # Example: self.test_best_match_across_chunks_and_top_k_limit()
    def test_best_match_across_chunks_and_top_k_limit(self):
        """A later email chunk can improve a page's rank and match metadata."""

        first = dict(
            page_id=1,
            path="services",
            title=None,
            wiki_url=None,
            chunk_index=0,
            chunk_text="Strategy",
            distance=0.4,
        )
        second = dict(first, page_id=2, path="contact", distance=0.2)
        improved = dict(first, chunk_index=3, distance=0.1)
        for top_k, expected_ids in ((1, ["1"]), (5, ["1", "2"])):
            with self.subTest(top_k=top_k):
                cursor, connection = make_cursor()
                cursor.fetchall.side_effect = [[first, second], [improved]]
                with patch(
                    "email_responder.storage.search.psycopg.connect",
                    return_value=connection,
                ):
                    pages = search.rank_pages("unused", [[1, 2], [3, 4]], top_k)
                self.assertEqual([page.page_id for page in pages], expected_ids)
                self.assertEqual(pages[0].best_distance, 0.1)
                self.assertEqual(pages[0].matched_email_chunk_index, 1)
                self.assertEqual(pages[0].matched_chunk_index, 3)
                self.assertEqual(pages[0].title, "services")
                self.assertEqual(pages[0].rank, 1)
                self.assertEqual(cursor.execute.call_args_list[0].args[1], ("[1,2]",))

    # Example: self.test_empty_knowledge_base_is_an_error()
    def test_empty_knowledge_base_is_an_error(self):
        """An empty index cannot produce an apparently grounded draft."""

        cursor, connection = make_cursor()
        cursor.fetchall.return_value = []
        with patch(
            "email_responder.storage.search.psycopg.connect", return_value=connection
        ):
            with self.assertRaisesRegex(RuntimeError, "embedding index"):
                search.rank_pages("unused", [[0.1]], 5)


# Example: python -m unittest tests.test_storage.HistoryTests
class HistoryTests(unittest.TestCase):
    """Both outcomes keep the existing database schema and JSON field names."""

    # Example: self.test_outcomes_store_body_pages_and_receipt()
    def test_outcomes_store_body_pages_and_receipt(self):
        """Success and failure serialize their details into the same history query."""

        email, page = make_email(), make_page()
        cursor, connection = make_cursor()
        with patch(
            "email_responder.storage.history.psycopg.connect", return_value=connection
        ):
            database = Database("unused")
            database.mark_replied(email, [page], "Answer", {"accepted": True})
            database.mark_failed(email, "Offline", [page], "Answer")
        success, failure = cursor.execute.call_args_list
        self.assertEqual(success.args[0], queries.SAVE_OUTCOME)
        self.assertEqual(success.args[1][1].obj, [page.to_dict()])
        self.assertEqual(success.args[1][4].obj, {"accepted": True})
        self.assertEqual(failure.args[1][4].obj, {"error": "Offline"})
        self.assertEqual(
            failure.args[1][6:], ("Offline", email.mailbox, email.message_key)
        )
