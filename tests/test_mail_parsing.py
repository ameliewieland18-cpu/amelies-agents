"""Edge cases at the boundary between raw email and the ordinary email object."""

import unittest
from datetime import UTC
from email.message import EmailMessage

from email_responder.mail.filtering import blocked_sender_reason
from email_responder.mail.identity import workflow_hash
from email_responder.mail.normalize import normalize_message
from email_responder.mail.parsing import parse_received_date
from email_responder.text import chunk_text
from tests.support import make_message, make_settings


# Example: python -m unittest tests.test_mail_parsing
class MailParsingTests(unittest.TestCase):
    """Preserve MIME handling, sender policy, and deterministic message identity."""

    # Example: self.test_html_fallback_ignores_attachments()
    def test_html_fallback_ignores_attachments(self):
        """Only the message body, not an attached text file, becomes reply context."""

        message = EmailMessage()
        message["From"] = "client@example.com"
        message.set_content("<p>Hello&nbsp;there</p>", subtype="html")
        message.add_attachment(
            "PRIVATE ATTACHMENT", subtype="plain", filename="notes.txt"
        )
        email = normalize_message(message, 1, make_settings())
        self.assertEqual(email.email_text, "Hello there")
        self.assertNotIn("PRIVATE", email.full_email)
        self.assertEqual(email.original_subject, "(no subject)")

    # Example: self.test_unknown_charset_falls_back_to_utf8()
    def test_unknown_charset_falls_back_to_utf8(self):
        """An unrecognized encoding label does not discard a readable body."""

        message = make_message(body="Hello")
        message["Content-Type"] = 'text/plain; charset="unknown-encoding"'
        self.assertEqual(
            normalize_message(message, 1, make_settings()).email_text, "Hello"
        )

    # Example: self.test_blocked_mail_can_have_no_body()
    def test_blocked_mail_can_have_no_body(self):
        """Blocked mail is recorded as skipped even without a usable body."""

        message = make_message(sender="news@mail.freelancer.com", body="")
        email = normalize_message(message, 1, make_settings())
        self.assertTrue(email.skip_before_reply)
        self.assertEqual(email.skip_reason, "blocked_sender")
        self.assertEqual(email.blocked_sender_domain, "freelancer.com")
        with self.assertRaisesRegex(ValueError, "body to answer"):
            normalize_message(make_message(body=""), 1, make_settings())

    # Example: self.test_domain_boundaries_and_display_name_keywords()
    def test_domain_boundaries_and_display_name_keywords(self):
        """Similar-looking domains are allowed; configured name keywords are blocked."""

        settings = make_settings()
        self.assertEqual(
            blocked_sender_reason("a@notfreelancer.com", "Client", settings), {}
        )
        reason = blocked_sender_reason("a@example.com", "Makro Market", settings)
        self.assertEqual(reason["blocked_sender_keyword"], "makro market")

    # Example: self.test_fallback_key_is_stable_and_reply_prefix_is_preserved()
    def test_fallback_key_is_stable_and_reply_prefix_is_preserved(self):
        """Missing Message-ID uses the same UID and content hash on repeated reads."""

        message = make_message()
        del message["Message-ID"]
        message.replace_header("Subject", "RE: Services")
        first = normalize_message(message, 42, make_settings())
        second = normalize_message(message, 42, make_settings())
        self.assertEqual(first.message_key, second.message_key)
        self.assertTrue(first.message_key.startswith("imap-uid:42:"))
        self.assertEqual(first.reply_subject, "RE: Services")
        self.assertEqual(workflow_hash("hello"), "bfb06f3a63cd7226")

    # Example: self.test_invalid_and_naive_dates_are_timezone_aware()
    def test_invalid_and_naive_dates_are_timezone_aware(self):
        """Cutoff comparisons can always use a timezone-aware timestamp."""

        for date in (None, "not a date", "Mon, 14 Sep 2026 12:00:00"):
            with self.subTest(date=date):
                self.assertEqual(parse_received_date(date).tzinfo, UTC)

    # Example: self.test_chunk_boundaries_and_invalid_sizes()
    def test_chunk_boundaries_and_invalid_sizes(self):
        """Paragraph grouping and long-block overlap retain the existing behavior."""

        self.assertEqual(
            chunk_text("one\n\ntwo\n\nthree", max_length=8, overlap=2),
            ["one\n\ntwo", "three"],
        )
        self.assertEqual(chunk_text(""), [])
        for length, overlap in ((0, 0), (3, -1), (3, 3)):
            with self.subTest(length=length, overlap=overlap):
                with self.assertRaises(ValueError):
                    chunk_text("text", length, overlap)
