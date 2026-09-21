"""Configuration and command selection without real credentials or services."""

import contextlib
import io
import os
import unittest
from unittest.mock import Mock, patch

from email_responder.app import main
from email_responder.config import Settings
from tests.support import make_settings


# Example: python -m unittest tests.test_configuration.SettingsTests
class SettingsTests(unittest.TestCase):
    """Environment strings should keep their existing defaults and conversions."""

    # Example: self.test_environment_conversion_and_overrides()
    def test_environment_conversion_and_overrides(self):
        """Account case, booleans, blocklists, numbers, and URL overrides survive."""

        environment = {
            "EMAIL_RESPONDER_ACCOUNT": "HELLO@EXAMPLE.COM",
            "EMAIL_RESPONDER_POLL_SECONDS": "1",
            "OPENAI_STORE_RESPONSES": " yes ",
            "EMAIL_RESPONDER_BLOCKED_DOMAINS": " EXAMPLE.COM, , mail.test ",
            "EMAIL_RESPONDER_BLOCKED_KEYWORDS": "",
            "DATABASE_URL": "postgresql://explicit",
            "EMAIL_RESPONDER_IMAP_PORT": "1993",
        }
        with patch.dict(os.environ, environment, clear=True):
            with patch("email_responder.environment.load_dotenv"):
                settings = Settings.from_environment()
        self.assertEqual(settings.account_email, "hello@example.com")
        self.assertEqual(settings.poll_seconds, 5)
        self.assertTrue(settings.store_openai_responses)
        self.assertEqual(settings.blocked_domains, ("example.com", "mail.test"))
        self.assertEqual(settings.blocked_keywords, ())
        self.assertEqual(settings.database_url, "postgresql://explicit")
        self.assertEqual(settings.imap_port, 1993)

    # Example: self.test_defaults_and_required_credentials()
    def test_defaults_and_required_credentials(self):
        """Defaults do not hide missing secrets; individual services can be optional."""

        with patch.dict(os.environ, {}, clear=True):
            with patch("email_responder.environment.load_dotenv"):
                settings = Settings.from_environment()
        self.assertEqual(
            settings.database_url,
            "postgresql://appuser:change-me-for-local-dev@127.0.0.1:5432/freelance",
        )
        with self.assertRaisesRegex(
            ValueError, "GMAIL_APP_PASSWORD, OPENAI_API_KEY, WIKIJS_API_TOKEN"
        ):
            settings.validate()
        settings.validate(
            require_gmail=False, require_openai=False, require_wikijs=False
        )


# Example: python -m unittest tests.test_configuration.CommandTests
class CommandTests(unittest.TestCase):
    """Dispatch each command to the intended workflow only."""

    # Example: self.setUp()
    def setUp(self):
        """Keep command-line logging setup from changing the test runner's logs."""

        logging_setup = patch("email_responder.app.configure_logging")
        logging_setup.start()
        self.addCleanup(logging_setup.stop)

    # Example: self.test_invalid_draft_flag_fails_before_loading_configuration()
    def test_invalid_draft_flag_fails_before_loading_configuration(self):
        """Draft-only cannot silently turn into an inbox run."""

        with patch("email_responder.app.Settings.from_environment") as load:
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    main(["--draft-only"])
        self.assertEqual(result.exception.code, 2)
        load.assert_not_called()

    # Example: self.test_baseline_needs_only_the_database()
    def test_baseline_needs_only_the_database(self):
        """Resetting the cutoff constructs no mail, wiki, or AI clients."""

        settings = make_settings(
            gmail_app_password="", openai_api_key="", wikijs_api_token=""
        )
        with patch(
            "email_responder.app.Settings.from_environment", return_value=settings
        ):
            with patch("email_responder.app.Database") as database:
                with patch("email_responder.app.build_responder") as build:
                    main(["--reset-baseline"])
        database.return_value.reset_baseline.assert_called_once_with(
            settings.account_email
        )
        build.assert_not_called()

    # Example: self.test_manual_preview_and_send_use_different_paths()
    def test_manual_preview_and_send_use_different_paths(self):
        """Only the explicit non-preview manual test can send a reply."""

        for draft_only in (False, True):
            with self.subTest(draft_only=draft_only):
                settings = make_settings(
                    gmail_app_password="" if draft_only else "test"
                )
                responder = Mock()
                responder.preview_email.return_value = "Preview body"
                arguments = ["--manual-test"] + (["--draft-only"] if draft_only else [])
                with patch(
                    "email_responder.app.Settings.from_environment",
                    return_value=settings,
                ):
                    with patch(
                        "email_responder.app.build_responder", return_value=responder
                    ):
                        with contextlib.redirect_stdout(io.StringIO()) as output:
                            main(arguments)
                if draft_only:
                    responder.process_email.assert_not_called()
                    self.assertEqual(output.getvalue(), "Preview body\n")
                else:
                    responder.preview_email.assert_not_called()
                    email = responder.process_email.call_args.args[0]
                    self.assertEqual(
                        email.sender_email, "hello+manual-test@example.com"
                    )

    # Example: self.test_once_and_forever_dispatch()
    def test_once_and_forever_dispatch(self):
        """Default polling exits cleanly on Ctrl+C; once invokes a single poll."""

        inbox = Mock()
        inbox.run_forever.side_effect = KeyboardInterrupt
        with patch(
            "email_responder.app.Settings.from_environment",
            return_value=make_settings(),
        ):
            with patch("email_responder.app.build_inbox", return_value=inbox):
                main(["--once"])
                main([])
        inbox.run_once.assert_called_once()
        inbox.run_forever.assert_called_once()
