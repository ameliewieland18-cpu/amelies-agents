"""Check the single-email workflow, especially when a reply must not be sent."""

import unittest
from unittest.mock import Mock, call

from email_responder.models import ClaimResult, ReplyDraft
from email_responder.responder import EmailResponder
from tests.support import make_email, make_page


# Example: python -m unittest tests.test_responder
class ResponderTests(unittest.TestCase):
    """Use stand-ins to observe workflow behavior without contacting services."""

    # Example: self.setUp()
    def setUp(self):
        """Supply a database, writer, and mailbox that record their calls."""

        self.services = Mock()
        self.database = self.services.database
        self.drafter = self.services.drafter
        self.gmail = self.services.gmail
        self.email = make_email()
        self.draft = ReplyDraft("Thanks for your question.", [make_page()])
        self.database.claim_email.return_value = ClaimResult(1, True, "processing", 3)
        self.drafter.create_draft.return_value = self.draft
        self.gmail.send_reply.return_value = {"accepted": True}
        self.responder = EmailResponder(self.database, self.drafter, self.gmail)

    # Example: self.test_success_claims_before_sending_and_records_afterward()
    def test_success_claims_before_sending_and_records_afterward(self):
        """A reply is sent only after claiming, and recorded only after sending."""

        self.assertEqual(self.responder.process_email(self.email), "replied")
        self.assertEqual(
            self.services.mock_calls,
            [
                call.database.claim_email(self.email),
                call.drafter.create_draft(self.email, 3),
                call.gmail.send_reply(self.email, self.draft.body),
                call.database.mark_replied(
                    self.email, self.draft.pages, self.draft.body, {"accepted": True}
                ),
            ],
        )

    # Example: self.test_ineligible_and_duplicate_messages_never_reach_services()
    def test_ineligible_and_duplicate_messages_never_reach_services(self):
        """Old, blocked, failed, processing, and replied records cannot send again."""

        for status in (
            "skipped_old",
            "skipped_blocked",
            "failed",
            "processing",
            "replied",
        ):
            with self.subTest(status=status):
                self.database.claim_email.return_value = ClaimResult(
                    1, False, status, 5
                )
                self.assertEqual(self.responder.process_email(self.email), status)
        self.drafter.create_draft.assert_not_called()
        self.gmail.send_reply.assert_not_called()

    # Example: self.test_preview_only_uses_the_writer()
    def test_preview_only_uses_the_writer(self):
        """Previewing never claims, sends, or writes a history record."""

        self.assertEqual(self.responder.preview_email(self.email), self.draft.body)
        self.assertEqual(
            self.services.mock_calls,
            [
                call.drafter.create_draft(self.email, 5),
            ],
        )

    # Example: self.test_failed_draft_never_sends()
    def test_failed_draft_never_sends(self):
        """A retrieval or writing failure stores an error without sending mail."""

        self.drafter.create_draft.side_effect = ValueError("No knowledge")
        with self.assertLogs("email_responder", level="ERROR"):
            self.assertEqual(self.responder.process_email(self.email), "failed")
        self.gmail.send_reply.assert_not_called()
        self.database.mark_failed.assert_called_once_with(
            self.email, "ValueError: No knowledge", pages=[], reply_body=""
        )

    # Example: self.test_failed_send_keeps_the_draft_for_inspection()
    def test_failed_send_keeps_the_draft_for_inspection(self):
        """A send failure retains the body and matched pages in its history."""

        self.gmail.send_reply.side_effect = RuntimeError("SMTP refused recipients")
        with self.assertLogs("email_responder", level="ERROR"):
            self.assertEqual(self.responder.process_email(self.email), "failed")
        self.database.mark_replied.assert_not_called()
        self.database.mark_failed.assert_called_once_with(
            self.email,
            "RuntimeError: SMTP refused recipients",
            pages=self.draft.pages,
            reply_body=self.draft.body,
        )

    # Example: self.test_history_failure_does_not_repeat_the_send()
    def test_history_failure_does_not_repeat_the_send(self):
        """Even if both history writes fail, sending is attempted just once."""

        self.database.mark_replied.side_effect = RuntimeError("Database offline")
        self.database.mark_failed.side_effect = RuntimeError("Still offline")
        with self.assertLogs("email_responder", level="ERROR") as logs:
            self.assertEqual(self.responder.process_email(self.email), "failed")
        self.assertEqual(len(logs.records), 2)
        self.gmail.send_reply.assert_called_once()
