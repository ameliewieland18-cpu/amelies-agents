"""Gmail protocol tests: unread fetching, mailbox flags, and threaded replies."""

import unittest
from unittest.mock import MagicMock, call, patch

from email_responder.services import imap, smtp
from tests.support import make_email, make_settings


# Example: python -m unittest tests.test_mail_services.ImapTests
class ImapTests(unittest.TestCase):
    """Fake IMAP response tuples to exercise unpacking without a mailbox."""

    # Example: self.test_fetch_skips_bad_records_and_uses_peek()
    def test_fetch_skips_bad_records_and_uses_peek(self):
        """A failed or malformed FETCH does not discard the next valid message."""

        connection = MagicMock()
        mailbox = connection.__enter__.return_value
        mailbox.select.return_value = ("OK", [])
        mailbox.uid.side_effect = [
            ("OK", [b"1 2 3"]),
            ("NO", []),
            ("OK", [b"metadata only", (b"incomplete",)]),
            ("OK", [(b"metadata", b"From: client@example.com\r\n\r\nHello"), b")"]),
        ]
        with patch(
            "email_responder.services.imap.imaplib.IMAP4_SSL", return_value=connection
        ):
            with self.assertLogs("email_responder", level="ERROR"):
                messages = imap.read_unseen(make_settings())
        self.assertEqual([uid for uid, message in messages], [3])
        self.assertEqual(messages[0][1]["From"], "client@example.com")
        self.assertEqual(
            mailbox.uid.call_args_list[-1], call("fetch", b"3", "(BODY.PEEK[])")
        )

    # Example: self.test_mark_seen_checks_mailbox_selection_and_store_result()
    def test_mark_seen_checks_mailbox_selection_and_store_result(self):
        """Read flags are written only after selecting the intended mailbox."""

        connection = MagicMock()
        mailbox = connection.__enter__.return_value
        with patch(
            "email_responder.services.imap.imaplib.IMAP4_SSL", return_value=connection
        ):
            mailbox.select.return_value = ("NO", [])
            with self.assertRaisesRegex(RuntimeError, "select IMAP"):
                imap.mark_seen(make_settings(), 42)
            mailbox.uid.assert_not_called()
            mailbox.select.return_value = ("OK", [])
            mailbox.uid.return_value = ("NO", [])
            with self.assertRaisesRegex(RuntimeError, "mark IMAP UID"):
                imap.mark_seen(make_settings(), 42)
            mailbox.uid.return_value = ("OK", [])
            imap.mark_seen(make_settings(), 42)
        self.assertEqual(
            mailbox.uid.call_args, call("store", "42", "+FLAGS", "(\\Seen)")
        )

    # Example: self.test_empty_search_and_failed_search()
    def test_empty_search_and_failed_search(self):
        """An empty inbox is normal; a failed search is an error."""

        connection = MagicMock()
        mailbox = connection.__enter__.return_value
        mailbox.select.return_value = ("OK", [])
        with patch(
            "email_responder.services.imap.imaplib.IMAP4_SSL", return_value=connection
        ):
            mailbox.uid.return_value = ("OK", [b""])
            self.assertEqual(imap.read_unseen(make_settings()), [])
            mailbox.uid.return_value = ("NO", [])
            with self.assertRaisesRegex(RuntimeError, "search"):
                imap.read_unseen(make_settings())


# Example: python -m unittest tests.test_mail_services.SmtpTests
class SmtpTests(unittest.TestCase):
    """Preserve recipient addresses, thread headers, and refusal handling."""

    # Example: self.test_reply_headers_and_refused_recipient()
    def test_reply_headers_and_refused_recipient(self):
        """Successful SMTP replies retain threading; refusals raise an error."""

        email = make_email()
        message = smtp.build_message(email, "Thank you!")
        self.assertEqual(message["To"], email.sender_email)
        self.assertEqual(message["In-Reply-To"], email.message_id)
        self.assertEqual(message["References"], email.message_id)
        self.assertEqual(message.get_content().strip(), "Thank you!")
        connection = MagicMock()
        server = connection.__enter__.return_value
        with patch(
            "email_responder.services.smtp.smtplib.SMTP_SSL", return_value=connection
        ):
            server.send_message.return_value = {}
            self.assertTrue(
                smtp.send_reply(make_settings(), email, "Thanks")["accepted"]
            )
            server.send_message.return_value = {email.sender_email: (550, b"Refused")}
            with self.assertRaisesRegex(RuntimeError, "refused recipients"):
                smtp.send_reply(make_settings(), email, "Thanks")
