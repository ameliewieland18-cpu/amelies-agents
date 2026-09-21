"""Check per-message isolation, read flags, and recovery between inbox polls."""

import unittest
from unittest.mock import Mock, call, patch

from email_responder.inbox import InboxRunner
from tests.support import make_message, make_settings


# Example: python -m unittest tests.test_inbox
class InboxTests(unittest.TestCase):
    """Failures in one message must not stop the inbox workflow."""

    # Example: self.test_each_message_is_handled_and_marked_read()
    def test_each_message_is_handled_and_marked_read(self):
        """Own mail and malformed mail are skipped; later valid mail still proceeds."""

        gmail, responder = Mock(), Mock()
        gmail.read_unseen.return_value = [
            (1, make_message(sender="hello@example.com")),
            (2, make_message(sender="")),
            (3, make_message()),
            (4, make_message()),
        ]
        responder.process_email.side_effect = [
            RuntimeError("Database offline"),
            "replied",
        ]
        gmail.mark_seen.side_effect = [RuntimeError("Flag failed"), None, None, None]
        inbox = InboxRunner(make_settings(), gmail, responder)

        with self.assertLogs("email_responder", level="ERROR"):
            self.assertEqual(inbox.run_once(), 4)
        self.assertEqual(responder.process_email.call_count, 2)
        self.assertEqual(
            gmail.mark_seen.call_args_list, [call(1), call(2), call(3), call(4)]
        )

    # Example: self.test_poll_failure_retries_and_interrupt_exits()
    def test_poll_failure_retries_and_interrupt_exits(self):
        """A temporary failure is retried after waiting; Ctrl+C terminates polling."""

        inbox = InboxRunner(make_settings(poll_seconds=12), Mock(), Mock())
        with patch.object(
            inbox, "run_once", side_effect=[OSError("Offline"), 0]
        ) as poll:
            with patch(
                "email_responder.inbox.time.sleep",
                side_effect=[None, KeyboardInterrupt],
            ) as sleep:
                with self.assertLogs("email_responder", level="ERROR"):
                    with self.assertRaises(KeyboardInterrupt):
                        inbox.run_forever()
        self.assertEqual(poll.call_count, 2)
        self.assertEqual(sleep.call_args_list, [call(12), call(12)])
